"""
Strategy 3: Bounceback — Q3 Halftime-Dip Specialist
Buy the favorite's contract at the start of Q3 when they're trailing
by a moderate margin. Exploits halftime pessimism selling on Kalshi
and the well-documented Q3 comeback pattern for strong favorites.
"""
import logging
from typing import Optional
from datetime import datetime

from core.models import (
    LiveGameState, EntrySignal, Position, Strategy, GameMode
)
from core.config import (
    GT_MIN_SPREAD, GT_ENTRY_WINDOW_Q3_SEC,
    GT_MIN_TRAILING_POINTS, GT_MAX_TRAILING_POINTS,
    GT_MIN_DEFICIT_VS_SPREAD,
    GT_MIN_PRICE_CENTS, GT_MAX_PRICE_CENTS,
    GT_MIN_PRICE_DROP_PCT, GT_MIN_BOOK_DEPTH,
    GT_MIN_EDGE_PCT,
    GT_BUDGET_PCT, GT_ENTRY1_BUDGET_SPLIT,
    GT_ENTRY2_MIN_DROP_PCT, GT_ENTRY2_MIN_TIME_Q3_SEC,
    GT_ENTRY2_MAX_DEFICIT,
    GT_TP1_PCT, GT_TP1_SELL_PCT,
    GT_TP2_PRICE_CENTS,
    GT_STOP_LOSS_PCT, GT_STOP_MIN_HOLD_SEC,
    GT_THESIS_INVALID_DEFICIT,
    GT_TIME_EXIT_Q4_SEC,
    GT_MAX_CONCURRENT_POSITIONS,
)
from strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class GarbageTimeStrategy(BaseStrategy):
    """
    Bounceback — Q3 Halftime-Dip Specialist.

    Targets strong favorites (spread >= 5) trailing by 6-18 points
    at the start of Q3. The halftime break creates a pessimism window
    where Kalshi retail traders dump positions, underpricing the
    favorite's comeback probability.

    Up to 2 entries per game. Simple take-profit ladder with tight stop.
    Remaining shares held for settlement (need ~30% win rate at 30¢ avg).
    """

    def __init__(self, positions: dict, bankroll_cents: int):
        super().__init__(Strategy.GARBAGE_TIME, positions)
        self.bankroll_cents = bankroll_cents
        self._tp1_taken: dict = {}  # position_id → bool

    def check_entry(self, state: LiveGameState) -> Optional[EntrySignal]:
        """Check entry conditions for Q3 bounceback."""
        if not self.is_game_tradeable(state):
            return None

        if self.has_position(state.game_id_espn):
            existing = self.get_position_for_game(state.game_id_espn)
            if existing:
                return self._check_second_entry(state, existing)
            return None

        return self._check_first_entry(state)

    def _check_first_entry(self, state: LiveGameState) -> Optional[EntrySignal]:
        """Entry 1: Buy the favorite at start of Q3 during halftime-dip."""

        # 1. Must be Q3, first 6 minutes (halftime dip window)
        if state.quarter != 3:
            return None
        if state.time_remaining_seconds < GT_ENTRY_WINDOW_Q3_SEC:
            return None

        # 2. Pre-game spread >= 5 (strong favorite)
        if state.opening_spread < GT_MIN_SPREAD:
            return None

        # 3. Favorite must be losing by 6-18 points (moderate deficit)
        trailing_by = -state.score_differential  # positive when favorite losing
        if trailing_by < GT_MIN_TRAILING_POINTS:
            return None
        if trailing_by > GT_MAX_TRAILING_POINTS:
            return None

        # 4. Deficit vs spread confirmation
        if state.deficit_vs_spread < GT_MIN_DEFICIT_VS_SPREAD:
            return None

        # 5. Kalshi price in the sweet spot: 15-42¢
        ask_price = state.kalshi_yes_ask
        if ask_price is None:
            return None
        if ask_price < GT_MIN_PRICE_CENTS or ask_price > GT_MAX_PRICE_CENTS:
            return None

        # 6. Price must have dropped meaningfully from tipoff
        if state.price_drop_from_tipoff < GT_MIN_PRICE_DROP_PCT:
            return None

        # 7. Minimum book depth
        if state.kalshi_book_depth < GT_MIN_BOOK_DEPTH:
            return None

        # 8. Edge confirmation (if fair value available — don't block without it)
        if state.edge_conservative is not None:
            if state.edge_conservative < GT_MIN_EDGE_PCT:
                return None

        # ─── SIZING: 14% of bankroll, 70% for entry 1 ───
        game_budget = int(self.bankroll_cents * GT_BUDGET_PCT)
        entry1_budget = int(game_budget * GT_ENTRY1_BUDGET_SPLIT)
        shares = entry1_budget // ask_price

        if shares < 1:
            return None

        # Confidence scales with spread strength and edge
        confidence = 65
        if state.opening_spread >= 7:
            confidence = 72
        if state.edge_conservative is not None and state.edge_conservative >= 0.10:
            confidence = 80

        reason = (
            f"Bounceback Entry 1: trailing by {trailing_by}, "
            f"spread={state.opening_spread}, "
            f"deficit_vs_spread={state.deficit_vs_spread:.1f}, "
            f"price={ask_price}¢, drop={state.price_drop_from_tipoff:.0%}, "
            f"edge={state.edge_conservative:.1%}" if state.edge_conservative else
            f"Bounceback Entry 1: trailing by {trailing_by}, "
            f"spread={state.opening_spread}, "
            f"deficit_vs_spread={state.deficit_vs_spread:.1f}, "
            f"price={ask_price}¢, drop={state.price_drop_from_tipoff:.0%}"
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

    def _check_second_entry(
        self, state: LiveGameState, position: Position
    ) -> Optional[EntrySignal]:
        """Entry 2: Average down if price dropped further but deficit hasn't exploded."""

        if position.entry_count >= 2:
            return None

        # Must still be Q3 with enough time
        if state.quarter != 3:
            return None
        if state.time_remaining_seconds < GT_ENTRY2_MIN_TIME_Q3_SEC:
            return None

        # Deficit must not have grown past threshold
        if state.deficit_vs_spread > GT_ENTRY2_MAX_DEFICIT:
            return None

        # Price must have dropped further from Entry 1
        last_entry = position.entries[-1] if position.entries else None
        if not last_entry:
            return None

        ask_price = state.kalshi_yes_ask
        if ask_price is None:
            return None

        last_price = last_entry.price_cents
        if last_price <= 0:
            return None

        price_drop = (last_price - ask_price) / last_price
        if price_drop < GT_ENTRY2_MIN_DROP_PCT:
            return None

        if state.kalshi_book_depth < GT_MIN_BOOK_DEPTH:
            return None

        # Sizing: remaining 30% of game budget
        game_budget = int(self.bankroll_cents * GT_BUDGET_PCT)
        entry2_budget = int(game_budget * (1 - GT_ENTRY1_BUDGET_SPLIT))
        shares = entry2_budget // ask_price

        if shares < 1:
            return None

        reason = (
            f"Bounceback Entry 2: price dropped {price_drop:.0%} "
            f"from Entry 1 ({last_price}¢→{ask_price}¢), "
            f"deficit_vs_spread={state.deficit_vs_spread:.1f}"
        )

        return self.build_signal(
            state=state,
            entry_number=2,
            suggested_shares=shares,
            suggested_cost_cents=shares * ask_price,
            budget_source="GAME_BUDGET",
            confidence=75,
            reason=reason,
        )

    def check_exit(self, state: LiveGameState, position: Position) -> Optional[dict]:
        """
        Exit logic for bounceback positions.
        TP1 scalp at +30%, TP2 at 50¢, tight stop, time exit late Q4.
        Remaining shares ride to settlement.
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
        return_pct = (current_price - avg_cost) / avg_cost
        position_id = position.position_id

        # ─── THESIS INVALID: deficit exploded ───
        if state.deficit_vs_spread > GT_THESIS_INVALID_DEFICIT:
            return {
                "action": "SELL_ALL",
                "shares": position.shares_remaining,
                "price_cents": current_price,
                "reason": (
                    f"Bounceback thesis invalid: deficit {state.deficit_vs_spread:.1f} "
                    f"> {GT_THESIS_INVALID_DEFICIT}"
                ),
            }

        # ─── STOP LOSS: -35% after 6 min hold ───
        if return_pct <= -GT_STOP_LOSS_PCT:
            hold_seconds = (datetime.utcnow() - position.created_at).total_seconds()
            if hold_seconds >= GT_STOP_MIN_HOLD_SEC:
                return {
                    "action": "SELL_ALL",
                    "shares": position.shares_remaining,
                    "price_cents": current_price,
                    "reason": (
                        f"Bounceback stop: {return_pct:.0%} after "
                        f"{hold_seconds / 60:.0f}min (avg {avg_cost:.0f}¢)"
                    ),
                }

        # ─── TP1: +30% → sell 50% ───
        if return_pct >= GT_TP1_PCT and position_id not in self._tp1_taken:
            shares_to_sell = max(1, int(position.shares_remaining * GT_TP1_SELL_PCT))
            self._tp1_taken[position_id] = True
            return {
                "action": "SELL_PARTIAL",
                "shares": shares_to_sell,
                "price_cents": current_price,
                "reason": (
                    f"Bounceback TP1: +{return_pct:.0%} "
                    f"(sell {GT_TP1_SELL_PCT:.0%}, hold rest for settlement)"
                ),
                "mark_capital_recovered": True,
            }

        # ─── TP2: price ≥ 50¢ → sell remaining (game competitive) ───
        if current_price >= GT_TP2_PRICE_CENTS and position_id in self._tp1_taken:
            return {
                "action": "SELL_ALL",
                "shares": position.shares_remaining,
                "price_cents": current_price,
                "reason": (
                    f"Bounceback TP2: price {current_price}¢ ≥ {GT_TP2_PRICE_CENTS}¢ "
                    f"(+{return_pct:.0%} from avg {avg_cost:.0f}¢)"
                ),
            }

        # ─── TIME EXIT: Q4 with < 5 min left → sell at market ───
        if state.quarter >= 4 and state.time_remaining_seconds < GT_TIME_EXIT_Q4_SEC:
            return {
                "action": "SELL_ALL",
                "shares": position.shares_remaining,
                "price_cents": current_price,
                "reason": (
                    f"Bounceback time exit: Q{state.quarter} "
                    f"{state.time_remaining_seconds}s left, "
                    f"price {current_price}¢ ({return_pct:+.0%})"
                ),
            }

        # Otherwise hold for settlement
        return None

    def update_bankroll(self, new_bankroll_cents: int):
        self.bankroll_cents = new_bankroll_cents
