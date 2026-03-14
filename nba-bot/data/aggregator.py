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
        self._kalshi_update_count = -1  # Start at -1 so first update (count=0) fetches orderbook

    def initialize(self):
        """
        Run once at startup.
        Discover Kalshi NBA markets and map them to teams.
        Skips opening prices to avoid Kalshi rate limits (38+ extra API calls).
        """
        logger.info("Initializing data aggregator...")
        self._discover_kalshi_markets(fetch_opening_prices=False)
        logger.info(f"Found {len(self.kalshi_market_map)} Kalshi NBA markets")

    def _discover_kalshi_markets(self, fetch_opening_prices: bool = True):
        """
        Find all open NBA winner markets on Kalshi and map to team names.
        fetch_opening_prices: if True, call get_opening_price per market (44+ API calls).
        Only do this at initialize; rediscover skips it to avoid Kalshi rate limits.
        """
        markets = self.kalshi.discover_nba_winner_markets()

        for ticker, market_data in markets.items():
            title = market_data.get("title", "")
            subtitle = market_data.get("subtitle", "")
            full_text = f"{title} {subtitle}".lower()

            # Try to extract team names from the market title/subtitle
            # Kalshi titles vary: "Lakers vs Celtics", "Will the Lakers win?", etc.
            # This is a best-effort extraction — may need refinement
            self.kalshi_market_map[ticker] = market_data

            if fetch_opening_prices:
                opening = self.kalshi.get_opening_price(ticker)
                if opening:
                    self._opening_prices[ticker] = opening

        logger.info(f"Kalshi market map: {list(self.kalshi_market_map.keys())}")

    def rediscover_and_rematch_markets(self):
        """
        Re-discover Kalshi NBA markets and re-match games that don't have a ticker.
        Call periodically — markets may appear when games are about to start.
        Does NOT fetch opening prices (44+ extra API calls) — avoids Kalshi rate limits.
        Does NOT overwrite live prices — update_kalshi_prices() handles that.
        """
        self._discover_kalshi_markets(fetch_opening_prices=False)
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

        matched_count = 0
        for game_id, state in self.games.items():
            game_odds = None
            if odds_source == "betstack":
                game_odds = self.betstack.find_game_odds(state.home_team, state.away_team)
            elif odds_source == "odds_api":
                game_odds = self.odds.find_game_odds(state.home_team, state.away_team)

            if game_odds:
                matched_count += 1
                state.fair_value_home = game_odds.get("fair_value_home")
                state.fair_value_away = game_odds.get("fair_value_away")
                state.current_spread = game_odds.get("current_spread")
                state.odds_last_updated = game_odds.get("timestamp")
                state.last_odds_update = datetime.utcnow()

                # If ESPN didn't provide a spread (game already live at startup),
                # use BetStack/Odds spread as fallback for opening_spread
                if state.opening_spread == 0 and state.current_spread is not None:
                    spread_val = abs(state.current_spread)
                    if spread_val > 0:
                        state.opening_spread = spread_val
                        # Fix favorite/underdog based on the spread
                        if state.current_spread < 0:
                            # Negative = home favored
                            state.favorite = state.home_team
                            state.underdog = state.away_team
                        else:
                            state.favorite = state.away_team
                            state.underdog = state.home_team
                        # Re-match Kalshi if favorite changed
                        self._match_kalshi_market(state)
                        logger.info(
                            f"Backfilled spread for {state.home_team} vs {state.away_team}: "
                            f"spread={spread_val}, favorite={state.favorite}"
                        )

                self._calculate_derived_signals(state)
            else:
                # Fallback: derive fair value from Kalshi prices when no odds source matches.
                # Kalshi yes_ask IS the market-implied probability for the yes team.
                self._apply_kalshi_fallback(state)

        logger.info(f"Odds update: matched {matched_count}/{len(self.games)} games")

    def update_kalshi_prices(self):
        """
        Fetch latest Kalshi prices for all matched markets.
        Call this every 10-15 seconds.
        Fetches orderbook every other update to reduce API calls.
        """
        # Start at -1 so first update (count=0) fetches orderbook
        self._kalshi_update_count += 1
        fetch_orderbook = (self._kalshi_update_count % 2) == 0

        matched_count = 0
        updated_count = 0

        for game_id, state in self.games.items():
            if not state.kalshi_market_ticker:
                continue
            matched_count += 1

            ticker = state.kalshi_market_ticker
            prices = self.kalshi.get_market_prices(ticker)

            if prices:
                bid = prices.get("yes_bid")
                ask = prices.get("yes_ask")
                last = prices.get("last_price")
                status = prices.get("status", "")

                state.kalshi_yes_bid = bid
                state.kalshi_yes_ask = ask
                state.kalshi_last_price = last
                state.kalshi_volume = prices.get("volume", 0)
                state.kalshi_open_interest = prices.get("open_interest", 0)
                state.kalshi_market_status = status
                state.last_kalshi_update = datetime.utcnow()
                updated_count += 1

                # Bid-ask spread
                if bid and ask:
                    state.kalshi_bid_ask_spread = ask - bid

                # Opening and tipoff prices
                if ticker in self._opening_prices:
                    state.kalshi_opening_price = self._opening_prices[ticker]
                if ticker in self._tipoff_prices:
                    state.kalshi_tipoff_price = self._tipoff_prices[ticker]

                # Order book depth
                if fetch_orderbook:
                    depth = self.kalshi.get_orderbook_depth_at_ask(ticker)
                    state.kalshi_book_depth = depth

                # If no fair value from BetStack/Odds, derive from Kalshi prices
                if state.fair_value_home is None and ask is not None:
                    self._apply_kalshi_fallback(state)
                else:
                    self._calculate_derived_signals(state)

                logger.debug(
                    f"Kalshi {ticker}: bid={bid} ask={ask} last={last} "
                    f"status={status} depth={state.kalshi_book_depth}"
                )
            else:
                logger.warning(f"Kalshi price fetch returned None for {ticker}")

        if matched_count > 0:
            logger.info(
                f"Kalshi prices: {updated_count}/{matched_count} markets updated"
                + (" (+ orderbook)" if fetch_orderbook else "")
            )

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

        # Kalshi ticker format: KXNBAGAME-26MAR14WASBOS-BOS
        # The middle segment contains both team codes concatenated (e.g., WASBOS)
        # The suffix after the last dash is the team "yes" represents

        for ticker, market_data in self.kalshi_market_map.items():
            # Extract the team-code segment from the ticker
            # e.g., "KXNBAGAME-26MAR14WASBOS-BOS" → middle part contains "WASBOS"
            parts = ticker.split("-")
            if len(parts) < 3:
                continue

            # The team codes are embedded in the date+teams segment (e.g., "26MAR14WASBOS")
            date_teams = parts[1]  # e.g., "26MAR14WASBOS"
            ticker_suffix = parts[-1]  # e.g., "BOS"

            # Check if both team abbreviations appear in the date+teams segment
            if home_abbrev not in date_teams or away_abbrev not in date_teams:
                continue

            # Pick the market where "yes" = favorite
            if ticker_suffix == fav_abbrev:
                state.kalshi_market_ticker = ticker
                state.kalshi_event_ticker = market_data.get("event_ticker")
                state.kalshi_yes_team = state.favorite
                # Use bid/ask from discover data so dashboard shows prices immediately
                bid = market_data.get("yes_bid")
                ask = market_data.get("yes_ask")
                last = market_data.get("last_price")
                state.kalshi_yes_bid = bid
                state.kalshi_yes_ask = ask
                state.kalshi_last_price = last
                state.last_kalshi_update = datetime.utcnow()
                self._calculate_derived_signals(state)
                logger.info(
                    f"Matched {state.home_team} vs {state.away_team} → {ticker} "
                    f"(yes={fav_abbrev}, bid={bid}, ask={ask}, last={last})"
                )
                return

        logger.warning(
            f"No Kalshi market found for {state.home_team} ({home_abbrev}) vs "
            f"{state.away_team} ({away_abbrev}) [fav={fav_abbrev}] — "
            f"searched {len(self.kalshi_market_map)} markets"
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
    # Kalshi-Based Fallback (when BetStack/Odds API fail to match)
    # ─────────────────────────────────────────

    def _apply_kalshi_fallback(self, state: LiveGameState):
        """
        When no odds source matches a game, derive fair value and spread
        from Kalshi's own market prices. Kalshi yes_ask is the market-implied
        probability for the yes team (the favorite).
        """
        if not state.kalshi_market_ticker or state.kalshi_yes_ask is None:
            return

        ask_cents = state.kalshi_yes_ask
        fav_prob = ask_cents / 100.0  # e.g., 62¢ → 0.62

        if fav_prob <= 0 or fav_prob >= 1:
            return

        # Set fair values based on which team "yes" represents
        if state.kalshi_yes_team == state.home_team:
            state.fair_value_home = fav_prob
            state.fair_value_away = 1.0 - fav_prob
        elif state.kalshi_yes_team == state.away_team:
            state.fair_value_home = 1.0 - fav_prob
            state.fair_value_away = fav_prob
        else:
            # Default: yes = home
            state.fair_value_home = fav_prob
            state.fair_value_away = 1.0 - fav_prob

        state.last_odds_update = datetime.utcnow()

        # Estimate spread from Kalshi probability if ESPN didn't provide one.
        # NBA rule of thumb: each point of spread ≈ 2.5-3% probability shift.
        # 50% = pick'em (spread 0), 60% ≈ spread 3, 70% ≈ spread 6, 80% ≈ spread 10
        if state.opening_spread == 0:
            estimated_spread = self._probability_to_spread(fav_prob)
            if estimated_spread > 0:
                state.opening_spread = estimated_spread
                # Favorite is already set from ESPN or Kalshi match
                # But fix it if it's still default (home_team)
                if state.kalshi_yes_team and state.favorite != state.kalshi_yes_team:
                    state.favorite = state.kalshi_yes_team
                    state.underdog = (
                        state.away_team if state.kalshi_yes_team == state.home_team
                        else state.home_team
                    )
                logger.info(
                    f"Kalshi fallback spread for {state.home_team} vs {state.away_team}: "
                    f"spread={estimated_spread:.1f} (from {ask_cents}¢ Kalshi ask), "
                    f"favorite={state.favorite}"
                )

        self._calculate_derived_signals(state)
        logger.info(
            f"Kalshi fallback fair value for {state.home_team} vs {state.away_team}: "
            f"fv_home={state.fair_value_home:.3f}, fv_away={state.fair_value_away:.3f}, "
            f"spread={state.opening_spread}"
        )

    @staticmethod
    def _probability_to_spread(prob: float) -> float:
        """
        Convert win probability to approximate NBA point spread.
        Based on historical NBA data: ~2.8% per point of spread.
        Returns absolute spread value (always positive).
        """
        if prob <= 0.5:
            return 0.0
        # Logit-based conversion: spread ≈ (prob - 0.5) / 0.028
        # Capped at reasonable NBA range
        spread = (prob - 0.5) / 0.028
        return round(min(spread, 20.0), 1)

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
