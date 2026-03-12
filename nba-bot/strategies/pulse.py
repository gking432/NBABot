"""
Aggressive momentum scalp strategy.
Frequent entries with tight profit targets and tight stops.
"""
import logging
from typing import Optional
from datetime import datetime

from core.models import LiveGameState, EntrySignal, Position, Strategy
from core.config import (
    PULSE_MIN_SPREAD, PULSE_MAX_SPREAD,
    PULSE_MIN_DEFICIT_VS_SPREAD, PULSE_MIN_PRICE_DROP_PCT,
    PULSE_MAX_ENTRY_PRICE_CENTS, PULSE_MIN_BOOK_DEPTH,
    PULSE_MAX_ENTRY_QUARTER,
    PULSE_BUDGET_PCT,
    PULSE_TP1_PCT, PULSE_TP1_SELL_PCT,
    PULSE_TP2_PCT, PULSE_TP2_SELL_PCT,
    PULSE_STOP_LOSS_PCT, PULSE_STOP_MIN_HOLD_MINUTES,
)
from strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class PulseStrategy(BaseStrategy):
    """
    Aggressive scalp strategy.
    Designed for high activity with small, fast wins and tight risk control.
    """

    def __init__(self, positions: dict, bankroll_cents: int):
        super().__init__(Strategy.PULSE, positions)
        self.bankroll_cents = bankroll_cents
        self._tp1_taken: dict = {}

    def check_entry(self, state: LiveGameState) -> Optional[EntrySignal]:
        if not self.is_game_tradeable(state):
            return None

        if self.has_position(state.game_id_espn):
            return None

        if state.quarter > PULSE_MAX_ENTRY_QUARTER:
            return None

        if not (PULSE_MIN_SPREAD <= state.opening_spread <= PULSE_MAX_SPREAD):
            return None

        if state.deficit_vs_spread < PULSE_MIN_DEFICIT_VS_SPREAD:
            return None

        if state.price_drop_from_tipoff < PULSE_MIN_PRICE_DROP_PCT:
            return None

        ask_price = state.kalshi_yes_ask
        if ask_price is None or ask_price > PULSE_MAX_ENTRY_PRICE_CENTS:
            return None

        if state.kalshi_book_depth < PULSE_MIN_BOOK_DEPTH:
            return None

        budget_cents = int(self.bankroll_cents * PULSE_BUDGET_PCT)
        shares = budget_cents // ask_price
        if shares < 1:
            return None

        reason = (
            f"Pulse entry: spread={state.opening_spread}, "
            f"deficit={state.deficit_vs_spread:.1f}, "
            f"price_drop={state.price_drop_from_tipoff:.0%}, "
            f"price={ask_price}¢, "
            f"Q{state.quarter} {state.time_remaining_seconds // 60}:{state.time_remaining_seconds % 60:02d}"
        )

        return self.build_signal(
            state=state,
            entry_number=1,
            suggested_shares=shares,
            suggested_cost_cents=shares * ask_price,
            budget_source="GAME_BUDGET",
            confidence=70,
            reason=reason,
        )

    def check_exit(self, state: LiveGameState, position: Position) -> Optional[dict]:
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

        if return_pct >= PULSE_TP1_PCT and position_id not in self._tp1_taken:
            shares_to_sell = max(1, int(position.shares_remaining * PULSE_TP1_SELL_PCT))
            self._tp1_taken[position_id] = True
            return {
                "action": "SELL_PARTIAL",
                "shares": shares_to_sell,
                "price_cents": current_price,
                "reason": f"Pulse TP1: +{return_pct:.0%} (sell {PULSE_TP1_SELL_PCT:.0%})",
            }

        if return_pct >= PULSE_TP2_PCT and position_id in self._tp1_taken:
            return {
                "action": "SELL_ALL",
                "shares": position.shares_remaining,
                "price_cents": current_price,
                "reason": f"Pulse TP2: +{return_pct:.0%} (sell remaining)",
            }

        if return_pct <= PULSE_STOP_LOSS_PCT:
            hold_seconds = (datetime.utcnow() - position.created_at).total_seconds()
            if hold_seconds >= PULSE_STOP_MIN_HOLD_MINUTES * 60:
                return {
                    "action": "SELL_ALL",
                    "shares": position.shares_remaining,
                    "price_cents": current_price,
                    "reason": f"Pulse stop: {return_pct:.0%} after {hold_seconds/60:.0f}min",
                }

        return None

    def update_bankroll(self, new_bankroll_cents: int):
        self.bankroll_cents = new_bankroll_cents
