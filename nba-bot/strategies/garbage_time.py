"""
Strategy 3: Garbage Time Favorite Lock
Buy the favorite's Kalshi contract during blowouts in Q3/Q4 when
the market price hasn't fully caught up to the near-certain outcome.
Single entry, no averaging down, high win-rate / small profit per trade.
"""
import logging
from typing import Optional

from core.models import (
    LiveGameState, EntrySignal, Position, Strategy, GameMode
)
from core.config import (
    GT_MIN_ENTRY_QUARTER, GT_Q3_MAX_TIME_REMAINING_SEC,
    GT_Q4_MIN_TIME_REMAINING_SEC,
    GT_MIN_LEAD_POINTS, GT_MIN_LEAD_HEAVY_FAV,
    GT_HEAVY_FAV_SPREAD_THRESHOLD,
    GT_MIN_FAVORITE_PRICE_CENTS, GT_MAX_FAVORITE_PRICE_CENTS,
    GT_MIN_BOOK_DEPTH, GT_MOMENTUM_FLOOR,
    GT_BUDGET_PCT,
    GT_TAKE_PROFIT_CENTS, GT_STOP_LOSS_LEAD_POINTS,
    GT_TIME_EXIT_Q4_REMAINING_SEC, GT_TIME_EXIT_PRICE_FLOOR_CENTS,
    GT_STOP_LOSS_PRICE_PCT,
    GT_MAX_CONCURRENT_POSITIONS,
)
from strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class GarbageTimeStrategy(BaseStrategy):
    """
    Garbage Time Favorite Lock.
    Buys the favorite when they're winning by 20+ in Q3/Q4 and
    the Kalshi price is still ≤93¢. Targets 97¢+ or settlement at 100¢.
    Single entry per game, no averaging down.
    """

    def __init__(self, positions: dict, bankroll_cents: int):
        super().__init__(Strategy.GARBAGE_TIME, positions)
        self.bankroll_cents = bankroll_cents

    def check_entry(self, state: LiveGameState) -> Optional[EntrySignal]:
        """Check entry conditions for garbage time favorite lock."""
        if not self.is_game_tradeable(state):
            return None

        # Only one entry per game, no additional entries
        if self.has_position(state.game_id_espn):
            return None

        return self._check_first_entry(state)

    def _check_first_entry(self, state: LiveGameState) -> Optional[EntrySignal]:
        """Single entry: buy the favorite's contract during a blowout."""

        # 1. Must be Q3 or Q4
        if state.quarter < GT_MIN_ENTRY_QUARTER:
            return None

        # 2. Time window: Q3 with ≤4:00 left, or Q4 with ≥6:00 left
        if state.quarter == 3 and state.time_remaining_seconds > GT_Q3_MAX_TIME_REMAINING_SEC:
            return None
        if state.quarter == 4 and state.time_remaining_seconds < GT_Q4_MIN_TIME_REMAINING_SEC:
            return None
        # Don't enter in OT (quarter >= 5) — too unpredictable
        if state.quarter >= 5:
            return None

        # 3. Favorite must be WINNING by a large margin
        favorite_lead = state.favorite_score - state.underdog_score
        min_lead = GT_MIN_LEAD_POINTS
        if state.opening_spread >= GT_HEAVY_FAV_SPREAD_THRESHOLD:
            min_lead = GT_MIN_LEAD_HEAVY_FAV

        if favorite_lead < min_lead:
            return None

        # 4. Kalshi price must be in the sweet spot: 80-93¢
        ask_price = state.kalshi_yes_ask
        if ask_price is None:
            return None
        if ask_price < GT_MIN_FAVORITE_PRICE_CENTS:
            return None
        if ask_price > GT_MAX_FAVORITE_PRICE_CENTS:
            return None

        # 5. Minimum book depth
        if state.kalshi_book_depth < GT_MIN_BOOK_DEPTH:
            return None

        # 6. Momentum check: the lead must not be actively collapsing
        if state.momentum_score < GT_MOMENTUM_FLOOR:
            return None

        # ─── SIZING: fixed 15% of bankroll ───
        budget = int(self.bankroll_cents * GT_BUDGET_PCT)
        shares = budget // ask_price

        if shares < 1:
            return None

        # Confidence scales with lead size and quarter
        confidence = min(95, 75 + (favorite_lead - min_lead) + (state.quarter - 3) * 5)

        reason = (
            f"Garbage Time entry: lead={favorite_lead}, "
            f"price={ask_price}¢, spread={state.opening_spread}, "
            f"Q{state.quarter} {state.time_remaining_seconds // 60}:"
            f"{state.time_remaining_seconds % 60:02d}"
        )

        return self.build_signal(
            state=state,
            entry_number=1,
            suggested_shares=shares,
            suggested_cost_cents=shares * ask_price,
            budget_source="GAME_BUDGET",
            confidence=confidence,
            reason=reason,
        )

    def check_exit(self, state: LiveGameState, position: Position) -> Optional[dict]:
        """
        Exit logic for garbage time.
        Simple: take profit at 97¢+, stop loss if lead collapses, time exit near end.
        """
        current_price = state.kalshi_yes_ask or state.kalshi_last_price
        if current_price is None or current_price == 0:
            return None

        if position.shares_remaining <= 0:
            return None

        avg_cost = position.avg_cost_cents
        if avg_cost == 0:
            return None

        position.update_highest_price(current_price)

        # ─── STOP LOSS: Lead collapsed ───
        favorite_lead = state.favorite_score - state.underdog_score
        if favorite_lead <= GT_STOP_LOSS_LEAD_POINTS:
            return {
                "action": "SELL_ALL",
                "shares": position.shares_remaining,
                "price_cents": current_price,
                "reason": (
                    f"GT stop: lead collapsed to {favorite_lead} "
                    f"(threshold {GT_STOP_LOSS_LEAD_POINTS})"
                ),
            }

        # ─── STOP LOSS: Price dropped too much from entry ───
        price_drop = (avg_cost - current_price) / avg_cost
        if price_drop >= GT_STOP_LOSS_PRICE_PCT:
            return {
                "action": "SELL_ALL",
                "shares": position.shares_remaining,
                "price_cents": current_price,
                "reason": (
                    f"GT hard stop: price {current_price}¢ is "
                    f"-{price_drop:.0%} from entry {avg_cost:.0f}¢"
                ),
            }

        # ─── TAKE PROFIT: Price hit 97¢+ ───
        if current_price >= GT_TAKE_PROFIT_CENTS:
            return {
                "action": "SELL_ALL",
                "shares": position.shares_remaining,
                "price_cents": current_price,
                "reason": f"GT take profit: {current_price}¢ >= {GT_TAKE_PROFIT_CENTS}¢",
            }

        # ─── TIME EXIT: Late Q4 at 95¢+ ───
        if (state.quarter == 4
                and state.time_remaining_seconds <= GT_TIME_EXIT_Q4_REMAINING_SEC
                and current_price >= GT_TIME_EXIT_PRICE_FLOOR_CENTS):
            return {
                "action": "SELL_ALL",
                "shares": position.shares_remaining,
                "price_cents": current_price,
                "reason": (
                    f"GT time exit: {current_price}¢ with "
                    f"{state.time_remaining_seconds}s left in Q4"
                ),
            }

        return None

    def update_bankroll(self, new_bankroll_cents: int):
        self.bankroll_cents = new_bankroll_cents
