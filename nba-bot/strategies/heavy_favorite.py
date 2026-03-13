"""
Strategy 3: Heavy Favorite Collapse
When a big Vegas favorite gets blown out early, buy at panic prices.
The wider the spread, the more confidence. Patient exits aiming for settlement.
"""
import logging
from typing import Optional
from datetime import datetime

from core.models import (
    LiveGameState, EntrySignal, Position, Strategy, GameMode
)
from core.config import (
    HF_MIN_SPREAD, HF_MIN_DEFICIT_VS_SPREAD,
    HF_MAX_ENTRY_PRICE_CENTS, HF_MIN_BOOK_DEPTH,
    HF_MAX_ENTRY_QUARTER, HF_ENTRY1_MIN_TIME_LEFT_Q2_SEC,
    HF_BASE_GAME_BUDGET_PCT,
    HF_SPREAD_8_10_MULT, HF_SPREAD_10_12_MULT, HF_SPREAD_12_PLUS_MULT,
    HF_CAPITAL_RECOVERY_MULT, HF_CAPITAL_RECOVERY_SELL_PCT,
    HF_HOUSE_MONEY_1_MULT, HF_HOUSE_MONEY_1_SELL_PCT,
    HF_HOUSE_MONEY_2_PRICE_CENTS, HF_HOUSE_MONEY_2_SELL_PCT,
    HF_TRAILING_STOP_PCT, HF_DEFENSIVE_HARD_FLOOR_PCT,
    HF_MAX_POSITION_LOSS_PCT, HF_ENTRY3_MIN_SPREAD,
    TIER_ENTRY2_Q3_WINDOW_SEC, TIER_ENTRY2_Q3_MIN_DROP_PCT,
    TIER_ENTRY2_Q3_MIN_BOOK_DEPTH,
    TIER_ENTRY2_MIN_ADDITIONAL_DROP_PCT,
    TIER_MIN_BOOK_DEPTH, TIER_ENTRY2_MIN_TIME_LEFT_Q2_SEC,
    TIER_ENTRY4_MIN_TIME_LEFT_Q2_SEC,
)
from strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class HeavyFavoriteStrategy(BaseStrategy):
    """
    Heavy favorite collapse strategy.
    Targets games where a team favored by 8+ points is losing badly early.
    Position sizing scales with the spread (wider = more confident = larger bet).
    More patient exits than tiered — expects settlement wins.
    """

    def __init__(self, positions: dict, bankroll_cents: int):
        super().__init__(Strategy.HEAVY_FAVORITE, positions)
        self.bankroll_cents = bankroll_cents

    def _get_spread_multiplier(self, spread: float) -> float:
        """
        The wider the spread, the more confident we are.
        Returns a multiplier for position sizing.
        """
        if spread >= 12:
            return HF_SPREAD_12_PLUS_MULT
        elif spread >= 10:
            return HF_SPREAD_10_12_MULT
        else:
            return HF_SPREAD_8_10_MULT

    def _get_game_budget(self, spread: float) -> int:
        """Calculate game budget based on spread-scaled sizing."""
        base = int(self.bankroll_cents * HF_BASE_GAME_BUDGET_PCT)
        multiplier = self._get_spread_multiplier(spread)
        return int(base * multiplier)

    def check_entry(self, state: LiveGameState) -> Optional[EntrySignal]:
        """Check entry conditions for heavy favorite collapse."""
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
        """Entry 1 for heavy favorite collapse."""

        # 1. Quarter must be 1 or early Q2
        if state.quarter > HF_MAX_ENTRY_QUARTER:
            return None
        if state.quarter == 2 and state.time_remaining_seconds < HF_ENTRY1_MIN_TIME_LEFT_Q2_SEC:
            return None

        # 2. Pre-game spread must be 8+
        if state.opening_spread < HF_MIN_SPREAD:
            return None

        # 3. Deficit vs spread >= 15
        if state.deficit_vs_spread < HF_MIN_DEFICIT_VS_SPREAD:
            return None

        # 4. Kalshi ask <= 30¢
        ask_price = state.kalshi_yes_ask
        if ask_price is None or ask_price > HF_MAX_ENTRY_PRICE_CENTS:
            return None

        # 5. Book depth >= 50
        if state.kalshi_book_depth < HF_MIN_BOOK_DEPTH:
            return None

        # ─── SIZING: spread-scaled ───
        game_budget = self._get_game_budget(state.opening_spread)
        entry1_budget = game_budget // 2  # 50% for entry 1
        shares = entry1_budget // ask_price

        if shares < 1:
            return None

        multiplier = self._get_spread_multiplier(state.opening_spread)
        confidence = int(70 + (state.opening_spread - 8) * 3)  # Higher spread = more confident
        confidence = min(95, confidence)

        reason = (
            f"Heavy Favorite Entry 1: spread={state.opening_spread}, "
            f"deficit={state.deficit_vs_spread:.1f}, price={ask_price}¢, "
            f"spread_mult={multiplier}x, "
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
        """Entry 2, 3, or 4 for heavy favorite (same logic as tiered)."""

        next_entry = position.entry_count + 1
        if next_entry > 4:
            return None

        if state.quarter > HF_MAX_ENTRY_QUARTER:
            return None

        # Time requirements
        if state.quarter == 2:
            if next_entry == 2 and state.time_remaining_seconds < TIER_ENTRY2_MIN_TIME_LEFT_Q2_SEC:
                return None
            if next_entry >= 4 and state.time_remaining_seconds < TIER_ENTRY4_MIN_TIME_LEFT_Q2_SEC:
                return None
        if state.quarter == 3 and next_entry != 2:
            return None

        # Price must have dropped further
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
        min_drop = TIER_ENTRY2_Q3_MIN_DROP_PCT if (next_entry == 2 and state.quarter == 3) else TIER_ENTRY2_MIN_ADDITIONAL_DROP_PCT
        if price_drop_since_last < min_drop:
            return None

        if next_entry >= 3 and state.opening_spread < HF_ENTRY3_MIN_SPREAD:
            return None

        min_depth = TIER_ENTRY2_Q3_MIN_BOOK_DEPTH if (next_entry == 2 and state.quarter == 3) else TIER_MIN_BOOK_DEPTH
        if state.kalshi_book_depth < min_depth:
            return None

        # ─── SIZING (spread-scaled for all entries) ───
        game_budget = self._get_game_budget(state.opening_spread)

        if next_entry == 2:
            budget = game_budget // 2
            budget_source = "GAME_BUDGET"
        else:
            nuclear_budget = game_budget  # Nuclear matches game budget for heavy favorite
            if next_entry == 3:
                budget = nuclear_budget // 2
            else:
                budget = nuclear_budget // 2
            budget_source = "NUCLEAR_RESERVE"

        shares = budget // ask_price
        if shares < 1:
            return None

        confidence = int(75 + (next_entry * 5))

        reason = (
            f"Heavy Favorite Entry {next_entry}: "
            f"price dropped {price_drop_since_last:.0%} since Entry {next_entry - 1}, "
            f"deficit={state.deficit_vs_spread:.1f}, price={ask_price}¢, "
            f"Q{state.quarter}"
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
        Exit logic for heavy favorite collapse.
        MORE PATIENT than tiered — we expect this team to win.
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
        position.current_mode = self.determine_game_mode(state, position)

        gain_multiple = current_price / avg_cost

        universal_stop_price = avg_cost * (1 - HF_MAX_POSITION_LOSS_PCT)
        if current_price <= universal_stop_price:
            loss_pct = (avg_cost - current_price) / avg_cost
            return {
                "action": "SELL_ALL",
                "shares": position.shares_remaining,
                "price_cents": current_price,
                "reason": (
                    f"HF universal tail stop: {current_price}¢ <= {universal_stop_price:.0f}¢ "
                    f"(-{loss_pct:.0%} from avg {avg_cost:.0f}¢)"
                ),
            }

        # ═══════════════════════════════════════
        # PROFITABLE EXITS (Patient House Money)
        # ═══════════════════════════════════════

        if not position.capital_recovered:
            # ─── CAPITAL RECOVERY: sell 35% at 2x (higher than tiered!) ───
            if gain_multiple >= HF_CAPITAL_RECOVERY_MULT:
                shares_to_sell = int(position.shares_remaining * HF_CAPITAL_RECOVERY_SELL_PCT)
                shares_to_sell = max(1, shares_to_sell)
                return {
                    "action": "SELL_PARTIAL",
                    "shares": shares_to_sell,
                    "price_cents": current_price,
                    "reason": f"HF Capital recovery: {gain_multiple:.1f}x (sell {HF_CAPITAL_RECOVERY_SELL_PCT:.0%})",
                    "mark_capital_recovered": True,
                }
        else:
            # ─── HOUSE MONEY 1: sell 20% at 3x ───
            if gain_multiple >= HF_HOUSE_MONEY_1_MULT and not position.house_money_1_hit:
                shares_to_sell = int(position.shares_remaining * HF_HOUSE_MONEY_1_SELL_PCT)
                shares_to_sell = max(1, shares_to_sell)
                return {
                    "action": "SELL_PARTIAL",
                    "shares": shares_to_sell,
                    "price_cents": current_price,
                    "reason": f"HF House money 1: {gain_multiple:.1f}x (sell {HF_HOUSE_MONEY_1_SELL_PCT:.0%})",
                    "mark_house_money_1": True,
                }

            # ─── HOUSE MONEY 2: sell 20% at 60¢+ ───
            if current_price >= HF_HOUSE_MONEY_2_PRICE_CENTS and not position.house_money_2_hit:
                shares_to_sell = int(position.shares_remaining * HF_HOUSE_MONEY_2_SELL_PCT)
                shares_to_sell = max(1, shares_to_sell)
                return {
                    "action": "SELL_PARTIAL",
                    "shares": shares_to_sell,
                    "price_cents": current_price,
                    "reason": f"HF House money 2: price at {current_price}¢",
                    "mark_house_money_2": True,
                }

            # ─── TRAILING STOP: 40% from peak (tighter than tiered) ───
            if position.highest_price_cents > 0:
                drop_from_peak = (position.highest_price_cents - current_price) / position.highest_price_cents
                if drop_from_peak >= HF_TRAILING_STOP_PCT:
                    return {
                        "action": "SELL_ALL",
                        "shares": position.shares_remaining,
                        "price_cents": current_price,
                        "reason": f"HF Trailing stop: {drop_from_peak:.0%} from peak {position.highest_price_cents}¢",
                    }

        # ═══════════════════════════════════════
        # LOSING EXITS (same mode system as tiered)
        # ═══════════════════════════════════════

        if position.current_mode == GameMode.OFFENSIVE:
            return None

        if position.current_mode == GameMode.NEUTRAL:
            return None

        if position.current_mode == GameMode.DEFENSIVE:
            if state.quarter >= 4:
                total_value = position.current_value_cents(current_price)
                if total_value < position.total_cost_cents * HF_DEFENSIVE_HARD_FLOOR_PCT:
                    return {
                        "action": "SELL_ALL",
                        "shares": position.shares_remaining,
                        "price_cents": current_price,
                        "reason": f"HF Hard floor: value {total_value}¢ in Q4",
                    }

            # Sell into strength
            if state.momentum_score > 0.3:
                return {
                    "action": "SELL_ALL",
                    "shares": position.shares_remaining,
                    "price_cents": current_price,
                    "reason": f"HF Defensive exit: selling into strength at {current_price}¢",
                }

        return None

    def update_bankroll(self, new_bankroll_cents: int):
        self.bankroll_cents = new_bankroll_cents
