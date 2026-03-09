"""
Data Aggregator.
Merges ESPN scores, The Odds API fair values, and Kalshi market prices
into a single LiveGameState per game.
"""
import logging
from typing import Dict, Optional, List
from datetime import datetime

from core.models import LiveGameState, GameStatus
from data.espn_client import ESPNClient
from data.odds_client import OddsClient
from data.betstack_client import BetStackClient
from data.kalshi_client import KalshiClient
from data.team_names import normalize_team_name, teams_match

logger = logging.getLogger(__name__)


class DataAggregator:
    """
    Merges all data sources into LiveGameState objects.
    Call update() on each main loop iteration.
    """

    def __init__(
        self,
        espn: ESPNClient,
        odds: OddsClient,
        kalshi: KalshiClient,
        betstack: BetStackClient = None,
    ):
        self.espn = espn
        self.odds = odds
        self.kalshi = kalshi
        self.betstack = betstack

        # Current state of all games
        self.games: Dict[str, LiveGameState] = {}  # game_id → LiveGameState

        # Kalshi market mapping: kalshi_ticker → (home_team, away_team)
        self.kalshi_market_map: Dict[str, dict] = {}

        # Tipoff price tracking: kalshi_ticker → first price at game start
        self._tipoff_prices: Dict[str, int] = {}
        self._opening_prices: Dict[str, int] = {}

        # Timing
        self._last_espn_update = 0.0
        self._last_odds_update = 0.0
        self._last_kalshi_update = 0.0

    def initialize(self):
        """
        Run once at startup.
        Discover Kalshi NBA markets and map them to teams.
        """
        logger.info("Initializing data aggregator...")
        self._discover_kalshi_markets()
        logger.info(f"Found {len(self.kalshi_market_map)} Kalshi NBA markets")

    def _discover_kalshi_markets(self):
        """Find all open NBA winner markets on Kalshi and map to team names."""
        markets = self.kalshi.discover_nba_winner_markets()

        for ticker, market_data in markets.items():
            title = market_data.get("title", "")
            subtitle = market_data.get("subtitle", "")
            full_text = f"{title} {subtitle}".lower()

            # Try to extract team names from the market title/subtitle
            # Kalshi titles vary: "Lakers vs Celtics", "Will the Lakers win?", etc.
            # This is a best-effort extraction — may need refinement
            self.kalshi_market_map[ticker] = market_data

            # Try to get opening price
            opening = self.kalshi.get_opening_price(ticker)
            if opening:
                self._opening_prices[ticker] = opening

        logger.info(f"Kalshi market map: {list(self.kalshi_market_map.keys())}")

    def rediscover_and_rematch_markets(self):
        """
        Re-discover Kalshi NBA markets and re-match games that don't have a ticker.
        Call periodically — markets may appear when games are about to start.
        """
        self._discover_kalshi_markets()
        # Re-match any games that don't have a Kalshi market yet
        for state in self.games.values():
            if not state.kalshi_market_ticker:
                self._match_kalshi_market(state)

    def update_scores(self) -> List[LiveGameState]:
        """
        Fetch latest scores from ESPN and update game states.
        Call this every 15 seconds.
        Returns list of updated LiveGameState objects.
        """
        espn_games = self.espn.get_live_games()

        for espn_game in espn_games:
            game_id = espn_game["game_id_espn"]

            if game_id not in self.games:
                # New game — create LiveGameState
                state = LiveGameState()
                state.game_id_espn = game_id
                state.game_id_nba = espn_game.get("game_id_nba")
                state.home_team = espn_game["home_team"]
                state.away_team = espn_game["away_team"]
                state.favorite = espn_game["favorite"]
                state.underdog = espn_game["underdog"]
                state.opening_spread = espn_game["opening_spread"]
                self.games[game_id] = state

                # Try to match with a Kalshi market
                self._match_kalshi_market(state)

            else:
                state = self.games[game_id]

            # Update live data
            was_pre = state.game_status == GameStatus.PRE
            state.home_score = espn_game["home_score"]
            state.away_score = espn_game["away_score"]
            state.quarter = espn_game["quarter"]
            state.time_remaining_seconds = espn_game["time_remaining_seconds"]
            state.game_status = espn_game["game_status"]
            state.last_score_update = datetime.utcnow()

            # Track tipoff price: when game transitions from PRE to LIVE
            if was_pre and state.game_status == GameStatus.LIVE:
                self._record_tipoff_prices(state)

            # Recalculate derived signals
            self._calculate_derived_signals(state)

        return list(self.games.values())

    def update_odds(self):
        """
        Fetch latest odds and update fair values.
        Primary: BetStack API (free, no monthly cap, 1 req/60s).
        Fallback: The Odds API (500/month — nearly exhausted).
        Only calls API when there are live games.
        """
        has_live = any(g.game_status == GameStatus.LIVE for g in self.games.values())
        if not has_live:
            return

        odds_source = None

        # Primary: BetStack
        if self.betstack and self.betstack.api_key:
            self.betstack.get_live_odds()
            odds_source = "betstack"
        # Fallback: The Odds API (only if BetStack unavailable)
        elif self.odds.quota_ok:
            logger.info("BetStack unavailable — falling back to The Odds API")
            self.odds.get_live_odds()
            odds_source = "odds_api"
        else:
            logger.warning("No odds source available — using cached values")
            return

        for game_id, state in self.games.items():
            game_odds = None
            if odds_source == "betstack":
                game_odds = self.betstack.find_game_odds(state.home_team, state.away_team)
            elif odds_source == "odds_api":
                game_odds = self.odds.find_game_odds(state.home_team, state.away_team)

            if game_odds:
                state.fair_value_home = game_odds.get("fair_value_home")
                state.fair_value_away = game_odds.get("fair_value_away")
                state.current_spread = game_odds.get("current_spread")
                state.odds_last_updated = game_odds.get("timestamp")
                state.last_odds_update = datetime.utcnow()

                self._calculate_derived_signals(state)

    def update_kalshi_prices(self):
        """
        Fetch latest Kalshi prices for all matched markets.
        Call this every 10-15 seconds.
        """
        for game_id, state in self.games.items():
            if not state.kalshi_market_ticker:
                continue

            ticker = state.kalshi_market_ticker
            prices = self.kalshi.get_market_prices(ticker)

            if prices:
                state.kalshi_yes_bid = prices.get("yes_bid")
                state.kalshi_yes_ask = prices.get("yes_ask")
                state.kalshi_last_price = prices.get("last_price")
                state.kalshi_volume = prices.get("volume", 0)
                state.kalshi_open_interest = prices.get("open_interest", 0)
                state.kalshi_market_status = prices.get("status", "")
                state.last_kalshi_update = datetime.utcnow()

                # Bid-ask spread
                if state.kalshi_yes_bid and state.kalshi_yes_ask:
                    state.kalshi_bid_ask_spread = state.kalshi_yes_ask - state.kalshi_yes_bid

                # Opening and tipoff prices
                if ticker in self._opening_prices:
                    state.kalshi_opening_price = self._opening_prices[ticker]
                if ticker in self._tipoff_prices:
                    state.kalshi_tipoff_price = self._tipoff_prices[ticker]

                # Order book depth
                depth = self.kalshi.get_orderbook_depth_at_ask(ticker)
                state.kalshi_book_depth = depth

                # Recalculate derived signals
                self._calculate_derived_signals(state)

    # ─────────────────────────────────────────
    # Kalshi Market Matching
    # ─────────────────────────────────────────

    def _match_kalshi_market(self, state: LiveGameState):
        """
        Try to match a LiveGameState with a Kalshi market ticker.
        Uses 3-letter team abbreviations from the ticker suffix (most reliable).
        Picks the market where "yes" = favorite, since strategies trade on
        the favorite coming back from a deficit.
        """
        from data.team_names import get_abbreviation

        home_abbrev = get_abbreviation(state.home_team)
        away_abbrev = get_abbreviation(state.away_team)
        fav_abbrev = get_abbreviation(state.favorite) if state.favorite else home_abbrev

        for ticker, market_data in self.kalshi_market_map.items():
            # Ticker format: KXNBAGAME-26FEB20BKNOKC-OKC
            # The suffix after the last dash is the team "yes" represents
            if not (home_abbrev in ticker and away_abbrev in ticker):
                continue

            # Pick the market where "yes" = favorite
            if ticker.endswith(f"-{fav_abbrev}"):
                state.kalshi_market_ticker = ticker
                state.kalshi_event_ticker = market_data.get("event_ticker")
                state.kalshi_yes_team = state.favorite
                logger.info(
                    f"Matched {state.home_team} vs {state.away_team} → {ticker} (yes={fav_abbrev})"
                )
                return

        logger.debug(
            f"No Kalshi market found for {state.home_team} ({home_abbrev}) vs {state.away_team} ({away_abbrev})"
        )

    def _record_tipoff_prices(self, state: LiveGameState):
        """Record the Kalshi price at the moment the game tips off."""
        if state.kalshi_market_ticker and state.kalshi_yes_ask:
            self._tipoff_prices[state.kalshi_market_ticker] = state.kalshi_yes_ask
            state.kalshi_tipoff_price = state.kalshi_yes_ask
            logger.info(
                f"Tipoff price for {state.kalshi_market_ticker}: {state.kalshi_yes_ask}¢"
            )

    # ─────────────────────────────────────────
    # Derived Signal Calculations
    # ─────────────────────────────────────────

    def _calculate_derived_signals(self, state: LiveGameState):
        """
        Calculate all derived metrics from raw data.
        This is where the raw numbers become trading signals.
        """

        # Score differential from favorite's perspective
        if state.favorite == state.home_team:
            state.score_differential = state.home_score - state.away_score
        else:
            state.score_differential = state.away_score - state.home_score

        # Deficit vs spread
        # If favorite is -5.5 and currently losing by 8, deficit_vs_spread = 13.5
        # (they're 13.5 points worse than expected)
        if state.opening_spread > 0:
            state.deficit_vs_spread = state.opening_spread - state.score_differential
            # Clamp to 0 — if favorite is ahead of spread, deficit is 0
            state.deficit_vs_spread = max(0, state.deficit_vs_spread)

        # Edge (Conservative strategy)
        # edge = fair_value - (kalshi_ask / 100)
        if state.fair_value_home is not None and state.kalshi_yes_ask is not None:
            # Use the fair value for whichever team "yes" represents
            if state.kalshi_yes_team == state.home_team:
                fair_value = state.fair_value_home
            elif state.kalshi_yes_team == state.away_team:
                fair_value = state.fair_value_away
            else:
                fair_value = state.fair_value_home

            state.edge_conservative = fair_value - (state.kalshi_yes_ask / 100.0)

        # Price drop from tipoff
        if state.kalshi_tipoff_price and state.kalshi_yes_ask:
            tipoff = state.kalshi_tipoff_price
            current = state.kalshi_yes_ask
            if tipoff > 0:
                state.price_drop_from_tipoff = (tipoff - current) / tipoff
                state.price_drop_from_tipoff = max(0, state.price_drop_from_tipoff)

    def get_live_games(self) -> List[LiveGameState]:
        """Return all current game states."""
        return list(self.games.values())

    def get_game(self, game_id: str) -> Optional[LiveGameState]:
        """Get state for a specific game."""
        return self.games.get(game_id)

    def cleanup_finished_games(self):
        """Remove games that have been final for over 30 minutes."""
        to_remove = []
        for game_id, state in self.games.items():
            if state.game_status == GameStatus.FINAL:
                if state.last_score_update:
                    elapsed = (datetime.utcnow() - state.last_score_update).total_seconds()
                    if elapsed > 1800:  # 30 minutes
                        to_remove.append(game_id)

        for game_id in to_remove:
            del self.games[game_id]
            logger.info(f"Cleaned up finished game: {game_id}")
