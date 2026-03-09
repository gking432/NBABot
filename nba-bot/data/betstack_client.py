"""
BetStack API client.
Drop-in replacement for OddsClient — fetches consensus odds and spreads.
Free tier: 1 request per 60 seconds, no monthly cap.
"""
import logging
import requests
from typing import Optional, Dict
from datetime import datetime

from core.config import BETSTACK_API_KEY
from data.team_names import normalize_team_name

logger = logging.getLogger(__name__)


class BetStackClient:
    """BetStack API client with fair value calculation from consensus odds."""

    BASE_URL = "https://api.betstack.dev/api/v1"

    def __init__(self):
        self.api_key = BETSTACK_API_KEY
        self.session = requests.Session()
        self.session.headers["X-API-Key"] = self.api_key

        self.requests_remaining: Optional[int] = None
        self.requests_used: int = 0

        self._last_odds: Dict[str, dict] = {}
        self._last_fetch_time: Optional[datetime] = None

    def _extract_team_name(self, team_field) -> str:
        """Extract team name whether it's a string or an object with a 'name' key."""
        if isinstance(team_field, dict):
            return team_field.get("name", "")
        return str(team_field) if team_field else ""

    def get_live_odds(self) -> Dict[str, dict]:
        """
        Fetch consensus odds for all NBA games.
        Returns dict of: {canonical_matchup_key: {home_team, away_team, fair_value_home, fair_value_away, current_spread}}

        Step 1: List all NBA events.
        Step 2: For each event, fetch detail (which includes lines).
        """
        if not self.api_key:
            logger.error("No BetStack API key configured")
            return self._last_odds

        try:
            url = f"{self.BASE_URL}/events"
            params = {"league": "basketball_nba"}

            resp = self.session.get(url, params=params, timeout=15)
            self.requests_used += 1

            if resp.status_code == 429:
                logger.warning("BetStack rate limited — using cached odds")
                return self._last_odds

            if resp.status_code != 200:
                logger.warning(f"BetStack API returned {resp.status_code}: {resp.text[:200]}")
                return self._last_odds

            data = resp.json()
            events = data if isinstance(data, list) else data.get("events", data.get("data", []))

            nba_events = []
            for event in events:
                league = event.get("league", {})
                league_key = league.get("key", "") if isinstance(league, dict) else str(league)
                if league_key == "basketball_nba" and not event.get("completed", False):
                    nba_events.append(event)

            odds_by_game = {}
            for event in nba_events:
                if event.get("lines"):
                    processed = self._process_event(event)
                    if processed:
                        key = self._make_game_key(processed["home_team"], processed["away_team"])
                        odds_by_game[key] = processed
                else:
                    event_id = event.get("id")
                    if event_id:
                        is_live = event.get("status") == "live"
                        cached_key = self._event_detail_cache_key(event)
                        if not is_live and cached_key and cached_key in self._last_odds:
                            odds_by_game[cached_key] = self._last_odds[cached_key]
                        else:
                            detail = self._fetch_event_detail(event_id)
                            if detail:
                                key = self._make_game_key(detail["home_team"], detail["away_team"])
                                odds_by_game[key] = detail

            self._last_odds = odds_by_game
            self._last_fetch_time = datetime.utcnow()

            logger.info(f"BetStack: fetched odds for {len(odds_by_game)} NBA games")
            return odds_by_game

        except requests.exceptions.RequestException as e:
            logger.warning(f"BetStack request failed: {e}")
            return self._last_odds
        except Exception as e:
            logger.error(f"BetStack error: {e}")
            return self._last_odds

    def _event_detail_cache_key(self, event: dict) -> Optional[str]:
        """Build a game key from the list-endpoint event for cache lookups."""
        try:
            home = normalize_team_name(self._extract_team_name(event.get("home_team", "")))
            away = normalize_team_name(self._extract_team_name(event.get("away_team", "")))
            if home and away:
                return self._make_game_key(home, away)
        except Exception:
            pass
        return None

    def _fetch_event_detail(self, event_id: int) -> Optional[dict]:
        """Fetch a single event's detail (includes lines)."""
        try:
            resp = self.session.get(f"{self.BASE_URL}/events/{event_id}", timeout=10)
            self.requests_used += 1
            if resp.status_code == 429:
                return None
            if resp.status_code != 200:
                return None
            return self._process_event(resp.json())
        except Exception as e:
            logger.debug(f"BetStack event {event_id} detail failed: {e}")
            return None

    def _process_event(self, event: dict) -> Optional[dict]:
        """
        Process a BetStack event into the same format as OddsClient.
        Extracts consensus moneyline -> fair value, and consensus spread.
        Handles both old (flat string) and new (nested object) API formats.
        """
        home_raw = event.get("home_team", "")
        away_raw = event.get("away_team", "")
        home_team = normalize_team_name(self._extract_team_name(home_raw))
        away_team = normalize_team_name(self._extract_team_name(away_raw))

        if not home_team or not away_team:
            return None

        lines = event.get("lines", event.get("line", None))
        if not lines:
            return None

        line = lines[0] if isinstance(lines, list) else lines

        ml_home, ml_away, spread_home = None, None, None

        # New format: moneyline is {"home": "205.0", "away": "-250.0"}
        moneyline = line.get("moneyline")
        if isinstance(moneyline, dict):
            ml_home = moneyline.get("home")
            ml_away = moneyline.get("away")
        else:
            # Old flat format
            ml_home = line.get("money_line_home")
            ml_away = line.get("money_line_away")

        # New format: spread is {"home": {"point": "7.0", ...}, "away": {...}}
        spread = line.get("spread")
        if isinstance(spread, dict):
            home_spread = spread.get("home", {})
            if isinstance(home_spread, dict):
                spread_home = home_spread.get("point")
            else:
                spread_home = home_spread
        else:
            spread_home = line.get("point_spread_home")

        if ml_home is None or ml_away is None:
            return None

        home_imp = self._american_to_probability(ml_home)
        away_imp = self._american_to_probability(ml_away)

        total = home_imp + away_imp
        if total <= 0:
            return None

        fair_value_home = home_imp / total
        fair_value_away = away_imp / total

        current_spread = float(spread_home) if spread_home is not None else None

        return {
            "home_team": home_team,
            "away_team": away_team,
            "fair_value_home": round(fair_value_home, 4),
            "fair_value_away": round(fair_value_away, 4),
            "current_spread": current_spread,
            "num_bookmakers": 1,
            "timestamp": datetime.utcnow(),
        }

    @staticmethod
    def _american_to_probability(odds) -> float:
        """Convert American odds to implied probability."""
        odds = int(float(odds))
        if odds < 0:
            return abs(odds) / (abs(odds) + 100)
        elif odds > 0:
            return 100 / (odds + 100)
        else:
            return 0.5

    @staticmethod
    def _make_game_key(home_team: str, away_team: str) -> str:
        return f"{home_team} vs {away_team}"

    def find_game_odds(self, home_team: str, away_team: str) -> Optional[dict]:
        """
        Find odds for a specific game from cached data.
        Same interface as OddsClient.find_game_odds().
        """
        home = normalize_team_name(home_team)
        away = normalize_team_name(away_team)

        key = self._make_game_key(home, away)
        if key in self._last_odds:
            return self._last_odds[key]

        key_reverse = self._make_game_key(away, home)
        if key_reverse in self._last_odds:
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

        for cached_key, odds in self._last_odds.items():
            if (normalize_team_name(odds["home_team"]) == home and
                    normalize_team_name(odds["away_team"]) == away):
                return odds

        return None

    @property
    def quota_ok(self) -> bool:
        """BetStack has no monthly cap — always OK as long as we respect the 60s rate limit."""
        return True

    @property
    def last_fetch_age_seconds(self) -> Optional[float]:
        if self._last_fetch_time is None:
            return None
        return (datetime.utcnow() - self._last_fetch_time).total_seconds()
