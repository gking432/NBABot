"""
Risk Manager.
Enforces all position limits, daily/weekly loss limits, and global kill switches.
Daily loss limit pauses the specific game, not the entire strategy.
Weekly loss limit and global hard floor pause the entire strategy.
"""
import logging
from typing import Dict, Set, Tuple
from datetime import datetime

from core.models import Strategy, EntrySignal
from core.config import (
    DAILY_LOSS_LIMIT_PCT, WEEKLY_LOSS_LIMIT_PCT, GLOBAL_HARD_FLOOR_PCT,
    CONS_MAX_CONCURRENT_POSITIONS, TIER_MAX_CONCURRENT_POSITIONS,
    TIER_CLASSIC_MAX_CONCURRENT_POSITIONS, GT_MAX_CONCURRENT_POSITIONS,
    PULSE_MAX_CONCURRENT_POSITIONS,
    INITIAL_BANKROLL_CENTS,
    PAPER_TRADING,
)

logger = logging.getLogger(__name__)


class RiskManager:
    """
    Enforces all risk limits.
    Every entry signal passes through here before execution.
    """

    def __init__(self, position_manager):
        self.pm = position_manager

        # Track daily starting balances
        self._daily_start: Dict[Strategy, int] = {}
        self._weekly_start: Dict[Strategy, int] = {}
        self._day_of_record: int = -1
        self._week_of_record: int = -1

        # Per-game pause: game IDs where we lost and hit daily loss threshold
        self._paused_games: Dict[Strategy, Set[str]] = {
            Strategy.CONSERVATIVE: set(),
            Strategy.TIERED: set(),
            Strategy.TIERED_CLASSIC: set(),
            Strategy.GARBAGE_TIME: set(),
            Strategy.CONSERVATIVE_HOLD: set(),
            Strategy.CONSERVATIVE_HOLD_FLIP: set(),
            Strategy.TIERED_HOLD: set(),
            Strategy.TIERED_HOLD_FLIP: set(),
            Strategy.TIERED_CLASSIC_HOLD: set(),
            Strategy.TIERED_FLIP: set(),
            Strategy.PULSE: set(),
        }

        # Strategy-wide pause (weekly loss or global floor only)
        self.strategy_paused: Dict[Strategy, bool] = {
            Strategy.CONSERVATIVE: False,
            Strategy.TIERED: False,
            Strategy.TIERED_CLASSIC: False,
            Strategy.GARBAGE_TIME: False,
            Strategy.CONSERVATIVE_HOLD: False,
            Strategy.CONSERVATIVE_HOLD_FLIP: False,
            Strategy.TIERED_HOLD: False,
            Strategy.TIERED_HOLD_FLIP: False,
            Strategy.TIERED_CLASSIC_HOLD: False,
            Strategy.TIERED_FLIP: False,
            Strategy.PULSE: False,
        }
        self.global_pause = False

        self.max_concurrent = {
            Strategy.CONSERVATIVE: CONS_MAX_CONCURRENT_POSITIONS,
            Strategy.TIERED: TIER_MAX_CONCURRENT_POSITIONS,
            Strategy.TIERED_CLASSIC: TIER_CLASSIC_MAX_CONCURRENT_POSITIONS,
            Strategy.GARBAGE_TIME: GT_MAX_CONCURRENT_POSITIONS,
            Strategy.CONSERVATIVE_HOLD: CONS_MAX_CONCURRENT_POSITIONS,
            Strategy.CONSERVATIVE_HOLD_FLIP: CONS_MAX_CONCURRENT_POSITIONS,
            Strategy.TIERED_HOLD: TIER_MAX_CONCURRENT_POSITIONS,
            Strategy.TIERED_HOLD_FLIP: TIER_MAX_CONCURRENT_POSITIONS,
            Strategy.TIERED_CLASSIC_HOLD: TIER_CLASSIC_MAX_CONCURRENT_POSITIONS,
            Strategy.TIERED_FLIP: TIER_MAX_CONCURRENT_POSITIONS,
            Strategy.PULSE: PULSE_MAX_CONCURRENT_POSITIONS,
        }

    def check_signal(self, signal: EntrySignal) -> Tuple[bool, str]:
        """
        Check if a signal is allowed by risk rules.
        Returns (allowed: bool, reason: str).
        """
        strategy = signal.strategy

        if self.global_pause:
            return False, "Global pause active — bankroll below hard floor"

        # Strategy-wide pause (weekly loss limit) is disabled in paper trading
        if not PAPER_TRADING and self.strategy_paused.get(strategy, False):
            return False, f"{strategy.value} paused due to weekly loss limit"

        # Per-game pause (daily loss limit hit on this game)
        if signal.game_id in self._paused_games.get(strategy, set()):
            return False, f"{strategy.value} paused for game {signal.game_id} (daily loss limit)"

        # Concurrent position limit
        current_count = self.pm.count_positions(strategy)
        max_allowed = self.max_concurrent.get(strategy, 2)
        if current_count >= max_allowed:
            return False, f"{strategy.value} at max positions ({current_count}/{max_allowed})"

        if signal.entry_number == 1 and current_count >= max_allowed:
            return False, f"No room for new {strategy.value} position"

        return True, "OK"

    def pause_game(self, strategy: Strategy, game_id: str):
        """Pause a specific game for a strategy after a losing position closes."""
        self._paused_games[strategy].add(game_id)
        logger.warning(
            f"GAME PAUSE: {strategy.value} paused for game {game_id} — "
            f"daily loss limit reached on this game"
        )

    def update_limits(self):
        """
        Check daily/weekly loss limits and activate kill switches.
        Call this on every main loop iteration.
        """
        now = datetime.utcnow()

        # New day: record starting balances, clear per-game pauses
        if now.day != self._day_of_record:
            self._day_of_record = now.day
            for strategy in Strategy:
                self._daily_start[strategy] = self.pm.bankrolls.get(strategy, 0)
                self._paused_games[strategy].clear()
            # Reset strategy-wide pauses (weekly resets on new week below)
            for strategy in Strategy:
                if self.strategy_paused.get(strategy):
                    logger.info(f"New day — resetting {strategy.value} pause")
                    self.strategy_paused[strategy] = False

        # New week: record weekly starting balances
        if now.isocalendar()[1] != self._week_of_record:
            self._week_of_record = now.isocalendar()[1]
            for strategy in Strategy:
                self._weekly_start[strategy] = self.pm.bankrolls.get(strategy, 0)

        # Daily loss check: only used for logging now.
        # Per-game pausing happens in position_manager when a position closes at a loss.
        for strategy in Strategy:
            daily_start = self._daily_start.get(strategy, 0)
            if daily_start <= 0:
                continue
            current = self.pm.bankrolls.get(strategy, 0)
            daily_loss_pct = (daily_start - current) / daily_start

            if daily_loss_pct >= DAILY_LOSS_LIMIT_PCT:
                logger.info(
                    f"Daily loss alert: {strategy.value} down {daily_loss_pct:.1%} today "
                    f"(limit {DAILY_LOSS_LIMIT_PCT:.0%}). Per-game pauses active."
                )

        # Weekly loss limits → strategy-wide pause (disabled in paper trading)
        if not PAPER_TRADING:
            for strategy in Strategy:
                weekly_start = self._weekly_start.get(strategy, 0)
                if weekly_start <= 0:
                    continue
                current = self.pm.bankrolls.get(strategy, 0)
                weekly_loss_pct = (weekly_start - current) / weekly_start

                if weekly_loss_pct >= WEEKLY_LOSS_LIMIT_PCT:
                    if not self.strategy_paused.get(strategy):
                        self.strategy_paused[strategy] = True
                        logger.warning(
                            f"KILL SWITCH: {strategy.value} paused — weekly loss "
                            f"{weekly_loss_pct:.1%} exceeds {WEEKLY_LOSS_LIMIT_PCT:.0%} limit"
                        )

        # Global hard floor
        total = sum(self.pm.bankrolls.values())
        floor = int(INITIAL_BANKROLL_CENTS * GLOBAL_HARD_FLOOR_PCT)
        if total < floor and not self.global_pause:
            self.global_pause = True
            logger.critical(
                f"GLOBAL KILL SWITCH: Total bankroll {total}¢ below "
                f"hard floor {floor}¢ ({GLOBAL_HARD_FLOOR_PCT:.0%} of start). "
                f"ALL TRADING PAUSED."
            )

    def get_status(self) -> dict:
        """Get current risk status for dashboard."""
        paused_games_count = sum(len(g) for g in self._paused_games.values())
        return {
            "global_pause": self.global_pause,
            "strategy_pauses": {s.value: v for s, v in self.strategy_paused.items()},
            "paused_games": {s.value: list(g) for s, g in self._paused_games.items()},
            "paused_games_count": paused_games_count,
            "bankrolls": {s.value: v for s, v in self.pm.bankrolls.items()},
            "total_bankroll": sum(self.pm.bankrolls.values()),
            "positions_count": {
                s.value: self.pm.count_positions(s) for s in Strategy
            },
        }
