"""
Strategy 2: Tiered (Quick Scalp)
Close-spread games, team falls behind early, buy the dip, take profit on the bounce.
Multi-entry averaging down. Quick-profit exits with hard stop loss.
"""
import logging
from typing import Optional
from datetime import datetime

from core.models import (
    LiveGameState, EntrySignal, Position, Strategy, GameMode, GameStatus
)
from core.config import (
    TIER_MIN_SPREAD, TIER_MAX_SPREAD,
    TIER_MIN_DEFICIT_VS_SPREAD, TIER_MIN_PRICE_DROP_PCT,
    TIER_MAX_ENTRY_PRICE_CENTS, TIER_MIN_BOOK_DEPTH,
    TIER_MAX_ENTRY_QUARTER,
    TIER_ENTRY2_MIN_ADDITIONAL_DROP_PCT, TIER_ENTRY2_MIN_ADDITIONAL_DEFICIT,
    TIER_ENTRY2_MIN_TIME_LEFT_Q2_SEC,
    TIER_ENTRY34_MIN_ADDITIONAL_DROP_PCT, TIER_ENTRY4_MIN_TIME_LEFT_Q2_SEC,
    TIER_GAME_BUDGET_PCT, TIER_NUCLEAR_BUDGET_PCT, TIER_MAX_PER_GAME_PCT,
    TIER_SCALP_PROFIT_PCT, TIER_SCALP_PARTIAL_SELL_PCT,
    TIER_SCALP_PRICE_TARGET_CENTS, TIER_SCALP_HIGH_AVG_TARGET_CENTS,
    TIER_SCALP_AVG_COST_THRESHOLD,
    TIER_SCALP_RECOVERY_ENTRIES,
    TIER_TIME_EXIT_Q4_SEC,
    NEUTRAL_MODE_Q3_WINDOW_SEC,
)
from strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class TieredStrategy(BaseStrategy):
    """
    Multi-entry price-drop strategy for close-spread games.
    Up to 4 entries per game. House money exit system.
    Time-based offensive/neutral/defensive modes.
    """

    def __init__(self, positions: dict, bankroll_cents: int):
        super().__init__(Strategy.TIERED, positions)
        self.bankroll_cents = bankroll_cents

    def check_entry(self, state: LiveGameState) -> Optional[EntrySignal]:
        """
        Check entry conditions.
        Handles Entry 1 (new position) and Entry 2-4 (averaging down).
        """
        if not self.is_game_tradeable(state):
            return None

        if self.has_position(state.game_id_espn):
            existing = self.get_position_for_game(state.game_id_espn)
            if existing:
                return self._check_additional_entry(state, existing)
            return None
        else:
            return self._check_first_entry(state)

    def _check_first_entry(self, state: LiveGameState) -> Optional[EntrySignal]:
        """Check conditions for Entry 1 (new position)."""

        # 1. Quarter must be 1 or 2
        if state.quarter > TIER_MAX_ENTRY_QUARTER:
            return None

        # 2. Pre-game spread between 1 and 7
        if not (TIER_MIN_SPREAD <= state.opening_spread <= TIER_MAX_SPREAD):
            return None

        # 3. Deficit vs spread >= 10
        if state.deficit_vs_spread < TIER_MIN_DEFICIT_VS_SPREAD:
            return None

        # 4. Price dropped >= 25% from tipoff
        if state.price_drop_from_tipoff < TIER_MIN_PRICE_DROP_PCT:
            return None

        # 5. Kalshi ask <= 35¢
        ask_price = state.kalshi_yes_ask
        if ask_price is None or ask_price > TIER_MAX_ENTRY_PRICE_CENTS:
            return None

        # 6. Book depth >= 50
        if state.kalshi_book_depth < TIER_MIN_BOOK_DEPTH:
            return None

        # ─── SIZING: 50% of game budget ───
        game_budget = int(self.bankroll_cents * TIER_GAME_BUDGET_PCT)
        entry1_budget = game_budget // 2
        shares = entry1_budget // ask_price

        if shares < 1:
            return None

        confidence = 65
        if state.price_drop_from_tipoff >= 0.40:
            confidence = 75
        if state.deficit_vs_spread >= 15:
            confidence = 80

        reason = (
            f"Tiered Entry 1: spread={state.opening_spread}, "
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
            confidence=confidence,
            reason=reason,
        )

    def _check_additional_entry(
        self, state: LiveGameState, position: Position
    ) -> Optional[EntrySignal]:
        """Check conditions for Entry 2, 3, or 4 (averaging down)."""

        next_entry = position.entry_count + 1
        if next_entry > 4:
            return None

        # Must still be Q1 or Q2
        if state.quarter > TIER_MAX_ENTRY_QUARTER:
            return None

        # Time requirements
        if state.quarter == 2:
            if next_entry == 2 and state.time_remaining_seconds < TIER_ENTRY2_MIN_TIME_LEFT_Q2_SEC:
                return None
            if next_entry >= 4 and state.time_remaining_seconds < TIER_ENTRY4_MIN_TIME_LEFT_Q2_SEC:
                return None

        # Price must have dropped further from last entry
        last_entry = position.entries[-1] if position.entries else None
        if not last_entry:
            return None

        ask_price = state.kalshi_yes_ask
        if ask_price is None:
            return None

        last_price = last_entry.price_cents
        if last_price <= 0:
            return None

        price_drop_since_last = (last_price - ask_price) / last_price
        min_drop = (TIER_ENTRY2_MIN_ADDITIONAL_DROP_PCT
                    if next_entry == 2
                    else TIER_ENTRY34_MIN_ADDITIONAL_DROP_PCT)

        if price_drop_since_last < min_drop:
            return None

        # Entry 2 requires deficit to have grown by 8+
        if next_entry == 2:
            # Estimate deficit at Entry 1 from the entry record
            deficit_growth = state.deficit_vs_spread - TIER_MIN_DEFICIT_VS_SPREAD
            if deficit_growth < TIER_ENTRY2_MIN_ADDITIONAL_DEFICIT:
                return None

        # No book depth check relaxation for additional entries
        if state.kalshi_book_depth < TIER_MIN_BOOK_DEPTH:
            return None

        # ─── SIZING ───
        if next_entry == 2:
            # Second half of game budget
            game_budget = int(self.bankroll_cents * TIER_GAME_BUDGET_PCT)
            budget = game_budget // 2
            budget_source = "GAME_BUDGET"
        else:
            # Nuclear reserve for Entry 3 and 4
            nuclear_budget = int(self.bankroll_cents * TIER_NUCLEAR_BUDGET_PCT)
            if next_entry == 3:
                budget = nuclear_budget // 2  # Split nuclear 50/50 for 3 and 4
            else:
                budget = nuclear_budget // 2
            budget_source = "NUCLEAR_RESERVE"

            # Check total allocation isn't exceeded
            max_total = int(self.bankroll_cents * TIER_MAX_PER_GAME_PCT)
            already_used = position.game_budget_used_cents + position.nuclear_budget_used_cents
            if already_used + budget > max_total:
                budget = max_total - already_used
                if budget <= 0:
                    return None

        shares = budget // ask_price
        if shares < 1:
            return None

        confidence = 70 + (next_entry * 5)  # Higher entry number = more conviction

        reason = (
            f"Tiered Entry {next_entry}: price dropped {price_drop_since_last:.0%} since Entry {next_entry - 1}, "
            f"deficit={state.deficit_vs_spread:.1f}, price={ask_price}¢, "
            f"Q{state.quarter} {state.time_remaining_seconds // 60}:{state.time_remaining_seconds % 60:02d}"
        )

        return self.build_signal(
            state=state,
            entry_number=next_entry,
            suggested_shares=shares,
            suggested_cost_cents=shares * ask_price,
            budget_source=budget_source,
            confidence=confidence,
            reason=reason,
        )

    def check_exit(self, state: LiveGameState, position: Position) -> Optional[dict]:
        """
        Quick Scalp exit logic.
        - 3+ entries: capital recovery mode (sell at breakeven or better)
        - 1-2 entries, avg < 30¢: sell 50% at +17.5%, sell rest at 40¢
        - 1-2 entries, avg >= 30¢: sell all at 48¢
        - Dynamic stop loss (Q3+): max loss = half of potential gain to 48¢
        - Time exit: sell all with < 5 min in Q4
        """
        current_price = state.kalshi_yes_ask or state.kalshi_last_price
        if current_price is None or current_price == 0:
            return None

        if position.shares_remaining <= 0:
            return None

        avg_cost = position.avg_cost_cents
        if avg_cost == 0:
            return None

        # ═══════════════════════════════════════
        # CAPITAL RECOVERY MODE (3+ entries)
        # ═══════════════════════════════════════

        if position.entry_count >= TIER_SCALP_RECOVERY_ENTRIES:
            if current_price >= avg_cost:
                gain_pct = (current_price - avg_cost) / avg_cost
                return {
                    "action": "SELL_ALL",
                    "shares": position.shares_remaining,
                    "price_cents": current_price,
                    "reason": (
                        f"Capital recovery ({position.entry_count} entries): "
                        f"{current_price}¢ >= avg {avg_cost:.0f}¢ (+{gain_pct:.1%})"
                    ),
                }

        # ═══════════════════════════════════════
        # PROFIT EXITS (1-2 entries)
        # ═══════════════════════════════════════

        if position.entry_count < TIER_SCALP_RECOVERY_ENTRIES:

            if avg_cost < TIER_SCALP_AVG_COST_THRESHOLD:
                # 2-stage exit: sell 50% at +17.5%, sell rest at 40¢
                profit_target = avg_cost * (1 + TIER_SCALP_PROFIT_PCT)

                if not position.capital_recovered and current_price >= profit_target:
                    shares_to_sell = max(1, int(position.shares_remaining * TIER_SCALP_PARTIAL_SELL_PCT))
                    gain_pct = (current_price - avg_cost) / avg_cost
                    return {
                        "action": "SELL_PARTIAL",
                        "shares": shares_to_sell,
                        "price_cents": current_price,
                        "reason": (
                            f"Quick scalp: {current_price}¢ is +{gain_pct:.0%} from "
                            f"avg {avg_cost:.0f}¢ (sell {TIER_SCALP_PARTIAL_SELL_PCT:.0%})"
                        ),
                        "mark_capital_recovered": True,
                    }

                if current_price >= TIER_SCALP_PRICE_TARGET_CENTS:
                    gain_pct = (current_price - avg_cost) / avg_cost
                    return {
                        "action": "SELL_ALL",
                        "shares": position.shares_remaining,
                        "price_cents": current_price,
                        "reason": (
                            f"Price target: {current_price}¢ >= "
                            f"{TIER_SCALP_PRICE_TARGET_CENTS}¢ (+{gain_pct:.0%})"
                        ),
                    }
            else:
                # Single exit: sell all at 48¢
                if current_price >= TIER_SCALP_HIGH_AVG_TARGET_CENTS:
                    gain_pct = (current_price - avg_cost) / avg_cost
                    return {
                        "action": "SELL_ALL",
                        "shares": position.shares_remaining,
                        "price_cents": current_price,
                        "reason": (
                            f"Price target: {current_price}¢ >= "
                            f"{TIER_SCALP_HIGH_AVG_TARGET_CENTS}¢ (+{gain_pct:.0%})"
                        ),
                    }

        # ═══════════════════════════════════════
        # DYNAMIC STOP LOSS (2:1 reward/risk, Q3+ only)
        # Max loss = half of potential gain to 48¢
        # Grace period: skip first 6 min of Q3 (halftime panic ≠ real game action)
        # ═══════════════════════════════════════

        q3_grace_elapsed = state.quarter > 3 or (
            state.quarter == 3 and state.time_remaining_seconds <= 720 - NEUTRAL_MODE_Q3_WINDOW_SEC
        )
        if state.quarter >= 3 and q3_grace_elapsed and position.entry_count < TIER_SCALP_RECOVERY_ENTRIES:
            potential_gain = TIER_SCALP_HIGH_AVG_TARGET_CENTS - avg_cost
            max_loss = potential_gain / 2
            stop_price = avg_cost - max_loss
            if current_price <= stop_price:
                loss_pct = (avg_cost - current_price) / avg_cost
                return {
                    "action": "SELL_ALL",
                    "shares": position.shares_remaining,
                    "price_cents": current_price,
                    "reason": (
                        f"Dynamic stop: {current_price}¢ <= {stop_price:.0f}¢ "
                        f"(2:1 R/R vs {TIER_SCALP_HIGH_AVG_TARGET_CENTS}¢ target, "
                        f"-{loss_pct:.0%} from avg {avg_cost:.0f}¢, Q{state.quarter})"
                    ),
                }

        # ═══════════════════════════════════════
        # TIME EXIT (Q4, < 5 min)
        # ═══════════════════════════════════════

        if state.quarter >= 4 and state.time_remaining_seconds < TIER_TIME_EXIT_Q4_SEC:
            pnl_pct = (current_price - avg_cost) / avg_cost
            return {
                "action": "SELL_ALL",
                "shares": position.shares_remaining,
                "price_cents": current_price,
                "reason": (
                    f"Time exit: Q4 with {state.time_remaining_seconds}s left, "
                    f"{current_price}¢ ({pnl_pct:+.0%} from avg {avg_cost:.0f}¢)"
                ),
            }

        return None

    def update_bankroll(self, new_bankroll_cents: int):
        """Update bankroll for position sizing."""
        self.bankroll_cents = new_bankroll_cents
