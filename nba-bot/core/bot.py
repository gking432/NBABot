"""
Main Bot Orchestrator.
Ties together data sources, strategies, position management, and risk.
This is the heartbeat of the system — runs every 15 seconds.
"""
import time
import logging
from typing import List
from datetime import datetime

from core.config import (
    MAIN_LOOP_INTERVAL, SNAPSHOT_INTERVAL, ODDS_POLL_INTERVAL,
    KALSHI_POLL_INTERVAL, KALSHI_REDISCOVER_INTERVAL, ESPN_POLL_INTERVAL, INJURY_CHECK_INTERVAL,
    INITIAL_BANKROLL_CENTS, PAPER_TRADING,
)
from core.models import (
    LiveGameState, GameStatus, Strategy, EntrySignal, Position
)
from core.database import Database
from data.espn_client import ESPNClient
from data.odds_client import OddsClient
from data.betstack_client import BetStackClient
from data.kalshi_client import KalshiClient
from data.aggregator import DataAggregator
from data.injury_detector import InjuryDetector
from strategies.conservative import ConservativeStrategy
from strategies.tiered import TieredStrategy
from strategies.tiered_classic import TieredClassicStrategy
from strategies.heavy_favorite import HeavyFavoriteStrategy
from strategies.hold import ConservativeHoldStrategy, TieredHoldStrategy, TieredClassicHoldStrategy
from strategies.pulse import PulseStrategy
from trading.position_manager import PositionManager
from trading.paper_engine import PaperTradingEngine
from trading.risk_manager import RiskManager

logger = logging.getLogger(__name__)


class TradingBot:
    """
    Main bot class.
    Initialize → run the main loop → update data → check strategies → manage positions.
    """

    def __init__(self):
        # ─── Data Layer ───
        self.db = Database()
        self.espn = ESPNClient()
        self.odds = OddsClient()
        self.betstack = BetStackClient()
        self.kalshi = KalshiClient()
        self.aggregator = DataAggregator(self.espn, self.odds, self.kalshi, self.betstack)
        self.injury_detector = InjuryDetector(self.espn)

        # ─── Trading Layer ───
        self.position_manager = PositionManager(self.db, self.injury_detector)
        self.paper_engine = PaperTradingEngine()
        self.risk_manager = RiskManager(self.position_manager)

        # ─── Strategy Layer ───
        self.position_manager.initialize_bankrolls(INITIAL_BANKROLL_CENTS)

        self.conservative = ConservativeStrategy(
            positions=self.position_manager.conservative_positions,
            bankroll_cents=self.position_manager.bankrolls[Strategy.CONSERVATIVE],
        )
        self.tiered = TieredStrategy(
            positions=self.position_manager.tiered_positions,
            bankroll_cents=self.position_manager.bankrolls[Strategy.TIERED],
        )
        self.tiered_classic = TieredClassicStrategy(
            positions=self.position_manager.tiered_classic_positions,
            bankroll_cents=self.position_manager.bankrolls[Strategy.TIERED_CLASSIC],
        )
        self.heavy_favorite = HeavyFavoriteStrategy(
            positions=self.position_manager.heavy_favorite_positions,
            bankroll_cents=self.position_manager.bankrolls[Strategy.HEAVY_FAVORITE],
        )

        self.conservative_hold = ConservativeHoldStrategy(
            positions=self.position_manager.conservative_hold_positions,
            bankroll_cents=self.position_manager.bankrolls[Strategy.CONSERVATIVE_HOLD],
        )
        self.tiered_hold = TieredHoldStrategy(
            positions=self.position_manager.tiered_hold_positions,
            bankroll_cents=self.position_manager.bankrolls[Strategy.TIERED_HOLD],
        )
        self.tiered_classic_hold = TieredClassicHoldStrategy(
            positions=self.position_manager.tiered_classic_hold_positions,
            bankroll_cents=self.position_manager.bankrolls[Strategy.TIERED_CLASSIC_HOLD],
        )
        self.pulse = PulseStrategy(
            positions=self.position_manager.pulse_positions,
            bankroll_cents=self.position_manager.bankrolls[Strategy.PULSE],
        )

        self.strategies = [
            self.conservative, self.tiered, self.tiered_classic, self.heavy_favorite,
            self.conservative_hold, self.tiered_hold, self.tiered_classic_hold,
            self.pulse,
        ]

        # ─── Timing ───
        self._last_espn_update = 0.0
        self._last_odds_update = 0.0
        self._last_kalshi_update = 0.0
        self._last_kalshi_rediscover = 0.0
        self._last_snapshot = 0.0
        self._last_injury_check = 0.0

        # ─── State ───
        self.running = False
        self.loop_count = 0

    def initialize(self):
        """One-time setup before the main loop starts."""
        logger.info("=" * 60)
        logger.info("NBA Trading Bot initializing...")
        logger.info(f"Mode: {'PAPER TRADING' if PAPER_TRADING else 'LIVE TRADING'}")
        logger.info(f"Initial bankroll: ${INITIAL_BANKROLL_CENTS / 100:.2f}")
        logger.info("=" * 60)

        # Verify Kalshi connection
        if self.kalshi.health_check():
            logger.info("Kalshi API: Connected")
        else:
            logger.error("Kalshi API: FAILED — check credentials")

        # Discover Kalshi NBA markets
        self.aggregator.initialize()

        # Initial data fetch
        logger.info("Fetching initial data...")
        self.aggregator.update_scores()
        self.aggregator.update_odds()
        self.aggregator.update_kalshi_prices()

        games = self.aggregator.get_live_games()
        live_games = [g for g in games if g.game_status == GameStatus.LIVE]
        logger.info(f"Found {len(games)} total games, {len(live_games)} live")

        self.running = True
        logger.info("Initialization complete. Starting main loop.")

    def run(self):
        """Main loop. Runs every MAIN_LOOP_INTERVAL seconds."""
        self.initialize()

        while self.running:
            try:
                loop_start = time.time()
                self.loop_count += 1

                self._main_loop_iteration()

                # Sleep for remaining interval
                elapsed = time.time() - loop_start
                sleep_time = max(0, MAIN_LOOP_INTERVAL - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

            except KeyboardInterrupt:
                logger.info("Bot stopped by user (Ctrl+C)")
                self.running = False
            except Exception as e:
                logger.error(f"Main loop error: {e}", exc_info=True)
                time.sleep(5)  # Brief pause before retrying

        logger.info("Bot stopped.")

    def _main_loop_iteration(self):
        """One iteration of the main loop."""
        now = time.time()

        # ─── Step 1: Update Data Sources ───

        # ESPN scores (every 15 seconds)
        if now - self._last_espn_update >= ESPN_POLL_INTERVAL:
            self.aggregator.update_scores()
            self._last_espn_update = now

        # Kalshi: re-discover markets periodically (they may appear when games start)
        if now - self._last_kalshi_rediscover >= KALSHI_REDISCOVER_INTERVAL:
            self.aggregator.rediscover_and_rematch_markets()
            self._last_kalshi_rediscover = now

        # Kalshi prices (every 10-15 seconds)
        if now - self._last_kalshi_update >= KALSHI_POLL_INTERVAL:
            self.aggregator.update_kalshi_prices()
            self._last_kalshi_update = now

        # The Odds API (every 5 minutes — budget constrained)
        if now - self._last_odds_update >= ODDS_POLL_INTERVAL:
            self.aggregator.update_odds()
            self._last_odds_update = now

        # ─── Step 2: Log Snapshots ───

        if now - self._last_snapshot >= SNAPSHOT_INTERVAL:
            for game in self.aggregator.get_live_games():
                if game.game_status in (GameStatus.LIVE, GameStatus.HALFTIME):
                    self.db.log_game_snapshot(game)
            self._last_snapshot = now

        # ─── Step 3: Update Risk Manager ───

        self.risk_manager.update_limits()

        # ─── Step 4: Update Strategy Bankrolls ───

        self.conservative.update_bankroll(
            self.position_manager.bankrolls[Strategy.CONSERVATIVE]
        )
        self.tiered.update_bankroll(
            self.position_manager.bankrolls[Strategy.TIERED]
        )
        self.tiered_classic.update_bankroll(
            self.position_manager.bankrolls[Strategy.TIERED_CLASSIC]
        )
        self.heavy_favorite.update_bankroll(
            self.position_manager.bankrolls[Strategy.HEAVY_FAVORITE]
        )
        self.conservative_hold.update_bankroll(
            self.position_manager.bankrolls[Strategy.CONSERVATIVE_HOLD]
        )
        self.tiered_hold.update_bankroll(
            self.position_manager.bankrolls[Strategy.TIERED_HOLD]
        )
        self.tiered_classic_hold.update_bankroll(
            self.position_manager.bankrolls[Strategy.TIERED_CLASSIC_HOLD]
        )
        self.pulse.update_bankroll(
            self.position_manager.bankrolls[Strategy.PULSE]
        )

        # ─── Step 5: Check Entries + Exits for Each Live Game ───

        processed_game_ids = set()
        for game in self.aggregator.get_live_games():
            if game.game_id_espn in processed_game_ids:
                continue
            processed_game_ids.add(game.game_id_espn)

            if game.game_status == GameStatus.LIVE:
                self._process_game(game)

            elif game.game_status == GameStatus.FINAL:
                self._handle_game_end(game)

        # ─── Step 6: Check Injuries ───

        if now - self._last_injury_check >= INJURY_CHECK_INTERVAL:
            self._check_injuries()
            self._last_injury_check = now

        # ─── Step 7: Cleanup ───

        self.aggregator.cleanup_finished_games()

        # ─── Periodic Logging ───

        if self.loop_count % 20 == 0:  # Every ~5 minutes
            status = self.risk_manager.get_status()
            total = status["total_bankroll"]
            logger.info(
                f"[Loop {self.loop_count}] Total bankroll: ${total / 100:.2f} | "
                f"Positions: {status['positions_count']} | "
                f"Pauses: {status['strategy_pauses']}"
            )

    def _process_game(self, state: LiveGameState):
        """Process a single live game: check entries, check exits."""

        # ─── CHECK EXITS FIRST (always, before entries) ───

        for strategy in self.strategies:
            positions = self.position_manager.get_positions_dict(strategy.name)
            if state.game_id_espn in positions:
                position = positions[state.game_id_espn]
                if position.is_active:
                    exit_info = strategy.check_exit(state, position)
                    if exit_info:
                        self.position_manager.execute_exit(position, state, exit_info)

                        # If position fully closed at a loss, pause this game (not the whole strategy)
                        if not position.is_active and position.realized_pnl_cents < 0:
                            self.risk_manager.pause_game(position.strategy, state.game_id_espn)

        # ─── CHECK ENTRIES ───

        for strategy in self.strategies:
            signal = strategy.check_entry(state)
            if signal:
                # Risk check
                allowed, reason = self.risk_manager.check_signal(signal)

                if allowed:
                    # Execute via paper or live engine
                    fill_price = self._get_fill_price(signal, state)
                    if fill_price:
                        signal.action_taken = True
                        self.position_manager.execute_entry(signal, state, fill_price)
                else:
                    signal.action_taken = False
                    signal.skip_reason = reason
                    logger.debug(f"Signal skipped: {reason}")

                # Log the signal regardless
                self.db.log_signal(signal)

    def _get_fill_price(self, signal: EntrySignal, state: LiveGameState) -> int:
        """Get fill price from paper or live engine."""
        if PAPER_TRADING:
            return self.paper_engine.simulate_buy_fill(signal, state)
        else:
            # Live trading — place real order on Kalshi
            # TODO: Implement in Week 4
            result = self.kalshi.place_order(
                ticker=state.kalshi_market_ticker,
                side="yes",
                action="buy",
                count=signal.suggested_shares,
                price_cents=signal.kalshi_price_cents,
            )
            if result:
                return signal.kalshi_price_cents  # Assume fill at limit price
            return None

    def _handle_game_end(self, state: LiveGameState):
        """Handle game settlement when a game goes final."""
        if state.game_status != GameStatus.FINAL:
            return

        # Determine winner
        if state.home_score > state.away_score:
            winner = state.home_team
        elif state.away_score > state.home_score:
            winner = state.away_team
        else:
            # Tie (NBA games can't tie, but handle it)
            logger.warning(f"Game {state.game_id_espn} appears tied — check manually")
            return

        # Settle all positions in this game
        self.position_manager.settle_game(state.game_id_espn, winner)

        # Clean up injury tracking
        self.injury_detector.clear_game(state.game_id_espn)

    def _check_injuries(self):
        """Run injury detection for all active positions."""
        active_positions = self.position_manager.get_all_active_positions()

        for position in active_positions:
            game = self.aggregator.get_game(position.game_id)
            if not game or game.game_status != GameStatus.LIVE:
                continue

            # Method 1: PBP absence
            events = self.injury_detector.check_pbp_absence(
                game_id=game.game_id_espn,
                game_id_nba=game.game_id_nba or "",
                team_name=position.team,
                current_game_time_seconds=game.total_game_seconds_elapsed,
            )

            for event in events:
                self.position_manager.handle_injury(event, game)

            # Method 2: Official report (less frequent)
            if self.loop_count % 4 == 0:  # Every ~4 injury check cycles
                official_events = self.injury_detector.check_official_report(
                    team_name=position.team
                )
                for event in official_events:
                    event.game_id = game.game_id_espn
                    self.position_manager.handle_injury(event, game)

    def get_status(self) -> dict:
        """Get full bot status for dashboard."""
        return {
            "running": self.running,
            "loop_count": self.loop_count,
            "mode": "PAPER" if PAPER_TRADING else "LIVE",
            "risk": self.risk_manager.get_status(),
            "live_games": [
                self._game_to_dict(g)
                for g in self.aggregator.get_live_games()
            ],
            "active_positions": [
                self._position_to_dict(p)
                for p in self.position_manager.get_all_active_positions()
            ],
            "odds_quota": {
                "remaining": self.odds.requests_remaining,
                "used": self.odds.requests_used,
            },
            "odds_source": "BetStack" if self.betstack.api_key else "The Odds API",
            "betstack_requests": self.betstack.requests_used,
        }

    def _game_to_dict(self, state: LiveGameState) -> dict:
        """Convert LiveGameState to dict for API/dashboard."""
        return {
            "game_id": state.game_id_espn,
            "home_team": state.home_team,
            "away_team": state.away_team,
            "home_score": state.home_score,
            "away_score": state.away_score,
            "quarter": state.quarter,
            "time_remaining": state.time_remaining_seconds,
            "status": state.game_status.value,
            "spread": state.opening_spread,
            "favorite": state.favorite,
            "kalshi_bid": state.kalshi_yes_bid,
            "kalshi_ask": state.kalshi_yes_ask,
            "kalshi_tipoff_price": state.kalshi_tipoff_price,
            "price_drop_pct": round(state.price_drop_from_tipoff * 100, 1),
            "fair_value": round(state.fair_value_home * 100, 1) if state.fair_value_home else None,
            "edge": round(state.edge_conservative * 100, 1) if state.edge_conservative else None,
            "deficit_vs_spread": round(state.deficit_vs_spread, 1),
            "book_depth": state.kalshi_book_depth,
        }

    def _position_to_dict(self, pos: Position) -> dict:
        """Convert Position to dict for API/dashboard."""
        return {
            "position_id": pos.position_id,
            "game_id": pos.game_id,
            "team": pos.team,
            "strategy": pos.strategy.value,
            "entry_count": pos.entry_count,
            "total_shares": pos.total_shares,
            "shares_remaining": pos.shares_remaining,
            "avg_cost_cents": round(pos.avg_cost_cents, 1),
            "total_cost_cents": pos.total_cost_cents,
            "status": pos.status.value,
            "capital_recovered": pos.capital_recovered,
            "mode": pos.current_mode.value,
            "highest_price_cents": pos.highest_price_cents,
            "capital_recovered": pos.capital_recovered,
            "house_money_1_hit": pos.house_money_1_hit,
            "house_money_2_hit": pos.house_money_2_hit,
            "q3_shaved": pos.q3_shaved,
            "entries": [
                {
                    "number": e.entry_number,
                    "price": e.price_cents,
                    "shares": e.shares,
                    "quarter": e.quarter,
                    "source": e.budget_source,
                }
                for e in pos.entries
            ],
        }
