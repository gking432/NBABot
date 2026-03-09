"""
The Odds API client.
Fetches live odds from Vegas sportsbooks and calculates fair value.
Budget: 500 requests/month on free tier — poll every 5 minutes during game hours.
"""
import logging
import statistics
import requests
from typing import Optional, Dict, List, Tuple
from datetime import datetime

from core.config import ODDS_API_KEY, ODDS_API_BASE_URL
from data.team_names import normalize_team_name

logger = logging.getLogger(__name__)


class OddsClient:
    """The Odds API client with fair value calculation and quota management."""

    def __init__(self):
        self.api_key = ODDS_API_KEY
        self.base_url = ODDS_API_BASE_URL
        self.session = requests.Session()

        # Quota tracking
        self.requests_remaining: Optional[int] = None
        self.requests_used: int = 0

        # Cache: store last fetched odds to use if quota runs out
        self._last_odds: Dict[str, dict] = {}  # game_key -> odds data
        self._last_fetch_time: Optional[datetime] = None

    def get_live_odds(self) -> Dict[str, dict]:
        """
        Fetch odds for all NBA games from US bookmakers.
        Returns dict of: {canonical_matchup_key: {home_team, away_team, fair_value_home, fair_value_away, current_spread}}

        Each API call returns ALL games, so one call covers everything.
        """
        if not self.api_key:
            logger.error("No Odds API key configured")
            return self._last_odds

        try:
            url = f"{self.base_url}/sports/basketball_nba/odds"
            params = {
                "apiKey": self.api_key,
                "regions": "us",
                "markets": "h2h,spreads",
                "oddsFormat": "american",
            }

            resp = self.session.get(url, params=params, timeout=15)

            # Track quota from response headers
            remaining = resp.headers.get("x-requests-remaining")
            if remaining is not None:
                self.requests_remaining = int(remaining)
                logger.info(f"Odds API quota remaining: {self.requests_remaining}")

            self.requests_used += 1

            if resp.status_code != 200:
                logger.warning(f"Odds API returned {resp.status_code}: {resp.text[:200]}")
                return self._last_odds

            data = resp.json()
            odds_by_game = {}

            for game in data:
                processed = self._process_game_odds(game)
                if processed:
                    key = self._make_game_key(processed["home_team"], processed["away_team"])
                    odds_by_game[key] = processed

            self._last_odds = odds_by_game
            self._last_fetch_time = datetime.utcnow()

            logger.info(f"Fetched odds for {len(odds_by_game)} NBA games")
            return odds_by_game

        except requests.exceptions.RequestException as e:
            logger.warning(f"Odds API request failed: {e}")
            return self._last_odds
        except Exception as e:
            logger.error(f"Odds API error: {e}")
            return self._last_odds

    def _process_game_odds(self, game: dict) -> Optional[dict]:
        """
        Process odds from multiple bookmakers into fair value.
        Fair value = median of vig-removed implied probabilities across all books.
        """
        home_team = normalize_team_name(game.get("home_team", ""))
        away_team = normalize_team_name(game.get("away_team", ""))

        if not home_team or not away_team:
            return None

        bookmakers = game.get("bookmakers", [])
        if not bookmakers:
            return None

        # Collect moneyline implied probabilities from each bookmaker
        home_probs = []
        away_probs = []
        spreads = []

        for book in bookmakers:
            markets = {m["key"]: m for m in book.get("markets", [])}

            # Moneyline (h2h) → fair value
            h2h = markets.get("h2h")
            if h2h:
                outcomes = {o["name"]: o["price"] for o in h2h.get("outcomes", [])}
                home_odds = outcomes.get(game.get("home_team"))
                away_odds = outcomes.get(game.get("away_team"))

                if home_odds is not None and away_odds is not None:
                    home_imp = self._american_to_probability(home_odds)
                    away_imp = self._american_to_probability(away_odds)

                    # Remove vig
                    total = home_imp + away_imp
                    if total > 0:
                        home_fair = home_imp / total
                        away_fair = away_imp / total
                        home_probs.append(home_fair)
                        away_probs.append(away_fair)

            # Spreads → current live spread
            spread_market = markets.get("spreads")
            if spread_market:
                for outcome in spread_market.get("outcomes", []):
                    if normalize_team_name(outcome.get("name", "")) == home_team:
                        point = outcome.get("point")
                        if point is not None:
                            spreads.append(float(point))

        if not home_probs:
            return None

        # Fair value = median across bookmakers (robust to outliers)
        fair_value_home = statistics.median(home_probs)
        fair_value_away = statistics.median(away_probs) if away_probs else (1 - fair_value_home)

        # Current live spread = median across bookmakers
        current_spread = statistics.median(spreads) if spreads else None

        return {
            "home_team": home_team,
            "away_team": away_team,
            "fair_value_home": round(fair_value_home, 4),
            "fair_value_away": round(fair_value_away, 4),
            "current_spread": current_spread,
            "num_bookmakers": len(home_probs),
            "timestamp": datetime.utcnow(),
        }

    @staticmethod
    def _american_to_probability(odds: int) -> float:
        """
        Convert American odds to implied probability.
        -220 → 0.6875 (68.75%)
        +180 → 0.3571 (35.71%)
        """
        if odds < 0:
            return abs(odds) / (abs(odds) + 100)
        elif odds > 0:
            return 100 / (odds + 100)
        else:
            return 0.5

    @staticmethod
    def _make_game_key(home_team: str, away_team: str) -> str:
        """Create a consistent key for matching games across APIs."""
        return f"{home_team} vs {away_team}"

    def find_game_odds(self, home_team: str, away_team: str) -> Optional[dict]:
        """
        Find odds for a specific game from the cached data.
        Handles team name normalization.
        """
        home = normalize_team_name(home_team)
        away = normalize_team_name(away_team)

        # Try direct match
        key = self._make_game_key(home, away)
        if key in self._last_odds:
            return self._last_odds[key]

        # Try reverse match (sometimes home/away is swapped between APIs)
        key_reverse = self._make_game_key(away, home)
        if key_reverse in self._last_odds:
            # Swap the values
            odds = self._last_odds[key_reverse]
            return {
                "home_team": home,
                "away_team": away,
                "fair_value_home": odds.get("fair_value_away"),
                "fair_value_away": odds.get("fair_value_home"),
                "current_spread": -odds.get("current_spread", 0) if odds.get("current_spread") else None,
                "num_bookmakers": odds.get("num_bookmakers", 0),
                "timestamp": odds.get("timestamp"),
            }

        # Fuzzy match: check all cached games
        for cached_key, odds in self._last_odds.items():
            if (normalize_team_name(odds["home_team"]) == home and
                    normalize_team_name(odds["away_team"]) == away):
                return odds

        return None

    @property
    def quota_ok(self) -> bool:
        """Check if we have quota remaining."""
        if self.requests_remaining is None:
            return True  # Unknown, assume OK
        return self.requests_remaining > 10  # Keep a buffer

    @property
    def last_fetch_age_seconds(self) -> Optional[float]:
        """How many seconds since last successful fetch."""
        if self._last_fetch_time is None:
            return None
        return (datetime.utcnow() - self._last_fetch_time).total_seconds()
