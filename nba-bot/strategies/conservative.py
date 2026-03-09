"""
Strategy 1: Conservative
Only enter when we can mathematically prove Kalshi is mispriced vs Vegas consensus.
Single entry. No averaging down. Mechanical take-profit exits.
"""
import logging
from typing import Optional
from datetime import datetime

from core.models import (
    LiveGameState, EntrySignal, Position, Strategy, GameMode
)
from core.config import (
    CONS_MIN_DEFICIT_VS_SPREAD, CONS_MIN_EDGE_PCT,
    CONS_MAX_ENTRY_PRICE_CENTS, CONS_MIN_BOOK_DEPTH,
    CONS_MAX_ENTRY_QUARTER,
    CONS_SIZE_EDGE_8_10, CONS_SIZE_EDGE_10_12, CONS_SIZE_EDGE_12_PLUS,
    CONS_TP1_PCT, CONS_TP1_SELL_PCT, CONS_TP2_PCT, CONS_TP2_SELL_PCT,
    CONS_STOP_LOSS_PCT, CONS_STOP_LOSS_MIN_HOLD_MINUTES,
    CONS_THESIS_INVALID_DEFICIT, CONS_THESIS_INVALID_MIN_QUARTER,
    CONS_THESIS_INVALID_MAX_TIME_SEC,
)
from strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class ConservativeStrategy(BaseStrategy):
    """
    Edge-based strategy.
    Enters when Kalshi price is significantly below Vegas fair value.
    Single entry, two-stage take profit, mechanical stop loss.
    """

    def __init__(self, positions: dict, bankroll_cents: int):
        super().__init__(Strategy.CONSERVATIVE, positions)
        self.bankroll_cents = bankroll_cents

        # Track which exits have been taken per position
        self._tp1_taken: dict = {}  # position_id → bool

    def check_entry(self, state: LiveGameState) -> Optional[EntrySignal]:
        """Check if conservative entry conditions are met."""

        # Basic tradability
        if not self.is_game_tradeable(state):
            return None

        # Already have a position?
        if self.has_position(state.game_id_espn):
            return None

        # ─── ENTRY CHECKLIST ───

        # 1. Quarter must be 1 or 2
        if state.quarter > CONS_MAX_ENTRY_QUARTER:
            return None

        # 2. Deficit vs spread must be >= 12
        if state.deficit_vs_spread < CONS_MIN_DEFICIT_VS_SPREAD:
            return None

        # 3. Edge must be >= 8%
        if state.edge_conservative is None or state.edge_conservative < CONS_MIN_EDGE_PCT:
            return None

        # 4. Kalshi ask price <= 35¢
        ask_price = state.kalshi_yes_ask
        if ask_price is None or ask_price > CONS_MAX_ENTRY_PRICE_CENTS:
            return None

        # 5. Order book depth >= 100
        if state.kalshi_book_depth < CONS_MIN_BOOK_DEPTH:
            return None

        # ─── SIZING ───
        edge = state.edge_conservative
        if edge >= 0.12:
            size_pct = CONS_SIZE_EDGE_12_PLUS
            confidence = 85
        elif edge >= 0.10:
            size_pct = CONS_SIZE_EDGE_10_12
            confidence = 75
        else:
            size_pct = CONS_SIZE_EDGE_8_10
            confidence = 65

        budget_cents = int(self.bankroll_cents * size_pct)
        shares = budget_cents // ask_price

        if shares < 1:
            return None

        reason = (
            f"Conservative entry: edge={edge:.1%}, deficit_vs_spread={state.deficit_vs_spread:.1f}, "
            f"price={ask_price}¢, fair_value={state.fair_value_home:.3f}, "
            f"Q{state.quarter} {state.time_remaining_seconds // 60}:{state.time_remaining_seconds % 60:02d}"
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
        Check all exit conditions for a conservative position.
        Returns: {action: "SELL_PARTIAL"|"SELL_ALL", shares: int, reason: str} or None
        """
        current_price = state.kalshi_yes_ask or state.kalshi_last_price
        if current_price is None or current_price == 0:
            return None

        if position.shares_remaining <= 0:
            return None

        avg_cost = position.avg_cost_cents
        if avg_cost == 0:
            return None

        return_pct = (current_price - avg_cost) / avg_cost
        position_id = position.position_id

        # ─── TAKE PROFIT 1: +30% → sell 50% ───
        if (return_pct >= CONS_TP1_PCT and
                position_id not in self._tp1_taken):
            shares_to_sell = int(position.shares_remaining * CONS_TP1_SELL_PCT)
            shares_to_sell = max(1, shares_to_sell)
            self._tp1_taken[position_id] = True

            return {
                "action": "SELL_PARTIAL",
                "shares": shares_to_sell,
                "price_cents": current_price,
                "reason": f"TP1: +{return_pct:.0%} (sell {CONS_TP1_SELL_PCT:.0%})",
            }

        # ─── TAKE PROFIT 2: +60% → sell remaining ───
        if (return_pct >= CONS_TP2_PCT and
                position_id in self._tp1_taken):
            return {
                "action": "SELL_ALL",
                "shares": position.shares_remaining,
                "price_cents": current_price,
                "reason": f"TP2: +{return_pct:.0%} (sell remaining)",
            }

        # ─── STOP LOSS: -30% AND held 12+ min AND deficit growing ───
        if return_pct <= CONS_STOP_LOSS_PCT:
            hold_seconds = (datetime.utcnow() - position.created_at).total_seconds()
            hold_minutes = hold_seconds / 60

            if hold_minutes >= CONS_STOP_LOSS_MIN_HOLD_MINUTES:
                # Check if deficit is still growing (not recovering)
                # A shrinking deficit means our thesis might still be alive
                if state.deficit_vs_spread >= CONS_MIN_DEFICIT_VS_SPREAD:
                    return {
                        "action": "SELL_ALL",
                        "shares": position.shares_remaining,
                        "price_cents": current_price,
                        "reason": (
                            f"Stop loss: {return_pct:.0%} after {hold_minutes:.0f}min, "
                            f"deficit still {state.deficit_vs_spread:.1f}"
                        ),
                    }

        # ─── THESIS INVALIDATION: deficit > 25, Q3+, < 8 min ───
        if (state.deficit_vs_spread > CONS_THESIS_INVALID_DEFICIT and
                state.quarter >= CONS_THESIS_INVALID_MIN_QUARTER and
                state.time_remaining_seconds < CONS_THESIS_INVALID_MAX_TIME_SEC):
            return {
                "action": "SELL_ALL",
                "shares": position.shares_remaining,
                "price_cents": current_price,
                "reason": (
                    f"Thesis invalid: deficit {state.deficit_vs_spread:.1f} in "
                    f"Q{state.quarter} with {state.time_remaining_seconds // 60}min left"
                ),
            }

        return None

    def update_bankroll(self, new_bankroll_cents: int):
        """Update bankroll for position sizing."""
        self.bankroll_cents = new_bankroll_cents
