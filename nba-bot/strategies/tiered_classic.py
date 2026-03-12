"""
Strategy 2b: Tiered Classic (reachable ladder + tail-risk caps)
Kept for A/B while Tiered V2 evolves.
"""
import logging
from typing import Optional

from core.models import LiveGameState, EntrySignal, Position, Strategy, GameMode
from core.config import (
    TIER_MIN_SPREAD,
    TIER_MAX_SPREAD,
    TIER_CLOSE_SPREAD_MAX,
    TIER_CLOSE_MAX_ENTRIES,
    TIER_MIN_DEFICIT_VS_SPREAD,
    TIER_MIN_PRICE_DROP_PCT,
    TIER_MIN_BOOK_DEPTH,
    TIER_MAX_ENTRY_QUARTER,
    TIER_ENTRY2_MIN_ADDITIONAL_DROP_PCT,
    TIER_ENTRY2_MIN_ADDITIONAL_DEFICIT,
    TIER_ENTRY2_MIN_TIME_LEFT_Q2_SEC,
    TIER_ENTRY34_MIN_ADDITIONAL_DROP_PCT,
    TIER_ENTRY4_MIN_TIME_LEFT_Q2_SEC,
    TIER_ENTRY3_MIN_SPREAD,
    TIER_ENTRY2_Q3_WINDOW_SEC,
    TIER_ENTRY2_Q3_MIN_DROP_PCT,
    TIER_ENTRY2_Q3_DEFICIT_GROWTH,
    TIER_ENTRY2_Q3_MIN_BOOK_DEPTH,
    TIER_GAME_BUDGET_PCT,
    TIER_NUCLEAR_BUDGET_PCT,
    TIER_MAX_PER_GAME_PCT,
    TIER_CLASSIC_MAX_ENTRY_PRICE_CENTS,
    TIER_CLASSIC_CAPITAL_RECOVERY_MULT,
    TIER_CLASSIC_CAPITAL_RECOVERY_SELL_PCT,
    TIER_CLASSIC_HOUSE_MONEY_1_MULT,
    TIER_CLASSIC_HOUSE_MONEY_1_SELL_PCT,
    TIER_CLASSIC_HOUSE_MONEY_2_MULT,
    TIER_CLASSIC_HOUSE_MONEY_2_SELL_PCT,
    TIER_CLASSIC_LATE_GAME_PRICE_CENTS,
    TIER_CLASSIC_LATE_GAME_SELL_PCT,
    TIER_CLASSIC_TRAILING_STOP_PCT,
    TIER_CLASSIC_DEFENSIVE_HARD_FLOOR_PCT,
    TIER_CLASSIC_UNIVERSAL_STOP_PCT,
    TIER_CLASSIC_RECOVERY_ENTRIES,
    TIER_CLASSIC_RECOVERY_STOP_LOSS_PCT,
    TIER_CLASSIC_MAX_POSITION_LOSS_PCT,
    NEUTRAL_MODE_Q3_WINDOW_SEC,
)
from strategies.base import BaseStrategy

logger = logging.getLogger(__name__)


class TieredClassicStrategy(BaseStrategy):
    def __init__(self, positions: dict, bankroll_cents: int, strategy: Strategy = Strategy.TIERED_CLASSIC):
        super().__init__(strategy, positions)
        self.bankroll_cents = bankroll_cents

    def _is_close_spread(self, state: LiveGameState) -> bool:
        return state.opening_spread <= TIER_CLOSE_SPREAD_MAX

    def check_entry(self, state: LiveGameState) -> Optional[EntrySignal]:
        if not self.is_game_tradeable(state):
            return None

        if self.has_position(state.game_id_espn):
            existing = self.get_position_for_game(state.game_id_espn)
            if existing:
                return self._check_additional_entry(state, existing)
            return None
        return self._check_first_entry(state)

    def _check_first_entry(self, state: LiveGameState) -> Optional[EntrySignal]:
        if state.quarter > TIER_MAX_ENTRY_QUARTER:
            if not (next_entry == 2 and state.quarter == 3 and
                    state.time_remaining_seconds >= TIER_ENTRY2_Q3_WINDOW_SEC):
                return None
        if not (TIER_MIN_SPREAD <= state.opening_spread <= TIER_MAX_SPREAD):
            return None
        if state.deficit_vs_spread < TIER_MIN_DEFICIT_VS_SPREAD:
            return None
        if state.price_drop_from_tipoff < TIER_MIN_PRICE_DROP_PCT:
            return None

        ask_price = state.kalshi_yes_ask
        if ask_price is None or ask_price > TIER_CLASSIC_MAX_ENTRY_PRICE_CENTS:
            return None
        if state.kalshi_book_depth < TIER_MIN_BOOK_DEPTH:
            return None

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
            f"Tiered Classic Entry 1: spread={state.opening_spread}, "
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

    def _check_additional_entry(self, state: LiveGameState, position: Position) -> Optional[EntrySignal]:
        next_entry = position.entry_count + 1
        if next_entry > 4:
            return None

        if self._is_close_spread(state) and next_entry > TIER_CLOSE_MAX_ENTRIES:
            return None

        if state.quarter > TIER_MAX_ENTRY_QUARTER:
            return None

        if state.quarter == 2:
            if next_entry == 2 and state.time_remaining_seconds < TIER_ENTRY2_MIN_TIME_LEFT_Q2_SEC:
                return None
            if next_entry >= 4 and state.time_remaining_seconds < TIER_ENTRY4_MIN_TIME_LEFT_Q2_SEC:
                return None
        if state.quarter == 3 and next_entry != 2:
            return None

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
        if next_entry == 2 and state.quarter == 3:
            min_drop = TIER_ENTRY2_Q3_MIN_DROP_PCT
        else:
            min_drop = TIER_ENTRY2_MIN_ADDITIONAL_DROP_PCT if next_entry == 2 else TIER_ENTRY34_MIN_ADDITIONAL_DROP_PCT
        if price_drop_since_last < min_drop:
            return None

        if next_entry == 2:
            deficit_growth = state.deficit_vs_spread - TIER_MIN_DEFICIT_VS_SPREAD
            min_growth = TIER_ENTRY2_Q3_DEFICIT_GROWTH if state.quarter == 3 else TIER_ENTRY2_MIN_ADDITIONAL_DEFICIT
            if deficit_growth < min_growth:
                return None

        if next_entry >= 3 and state.opening_spread < TIER_ENTRY3_MIN_SPREAD:
            return None

        min_depth = TIER_ENTRY2_Q3_MIN_BOOK_DEPTH if (next_entry == 2 and state.quarter == 3) else TIER_MIN_BOOK_DEPTH
        if state.kalshi_book_depth < min_depth:
            return None

        if next_entry == 2:
            game_budget = int(self.bankroll_cents * TIER_GAME_BUDGET_PCT)
            budget = game_budget // 2
            budget_source = "GAME_BUDGET"
        else:
            nuclear_budget = int(self.bankroll_cents * TIER_NUCLEAR_BUDGET_PCT)
            budget = nuclear_budget // 2
            budget_source = "NUCLEAR_RESERVE"

            max_total = int(self.bankroll_cents * TIER_MAX_PER_GAME_PCT)
            already_used = position.game_budget_used_cents + position.nuclear_budget_used_cents
            if already_used + budget > max_total:
                budget = max_total - already_used
                if budget <= 0:
                    return None

        shares = budget // ask_price
        if shares < 1:
            return None

        reason = (
            f"Tiered Classic Entry {next_entry}: price dropped {price_drop_since_last:.0%} since Entry {next_entry - 1}, "
            f"deficit={state.deficit_vs_spread:.1f}, price={ask_price}¢, "
            f"Q{state.quarter} {state.time_remaining_seconds // 60}:{state.time_remaining_seconds % 60:02d}"
        )

        return self.build_signal(
            state=state,
            entry_number=next_entry,
            suggested_shares=shares,
            suggested_cost_cents=shares * ask_price,
            budget_source=budget_source,
            confidence=70 + (next_entry * 5),
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

        position.update_highest_price(current_price)
        position.current_mode = self.determine_game_mode(state, position)
        gain_multiple = current_price / avg_cost

        universal_stop_price = avg_cost * (1 - TIER_CLASSIC_MAX_POSITION_LOSS_PCT)
        if current_price <= universal_stop_price:
            loss_pct = (avg_cost - current_price) / avg_cost
            return {
                "action": "SELL_ALL",
                "shares": position.shares_remaining,
                "price_cents": current_price,
                "reason": (
                    f"Classic universal tail stop: {current_price}¢ <= {universal_stop_price:.0f}¢ "
                    f"(-{loss_pct:.0%} from avg {avg_cost:.0f}¢)"
                ),
            }

        if position.entry_count >= TIER_CLASSIC_RECOVERY_ENTRIES:
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

            recovery_stop_price = avg_cost * (1 - TIER_CLASSIC_RECOVERY_STOP_LOSS_PCT)
            if current_price <= recovery_stop_price:
                loss_pct = (avg_cost - current_price) / avg_cost
                return {
                    "action": "SELL_ALL",
                    "shares": position.shares_remaining,
                    "price_cents": current_price,
                    "reason": (
                        f"Capital recovery stop: {current_price}¢ <= {recovery_stop_price:.0f}¢ "
                        f"(-{loss_pct:.0%} from avg {avg_cost:.0f}¢)"
                    ),
                }

        q3_grace_elapsed = state.quarter > 3 or (
            state.quarter == 3 and state.time_remaining_seconds <= 720 - NEUTRAL_MODE_Q3_WINDOW_SEC
        )
        if state.quarter >= 3 and q3_grace_elapsed:
            stop_price = avg_cost * (1 - TIER_CLASSIC_UNIVERSAL_STOP_PCT)
            if current_price <= stop_price:
                loss_pct = (avg_cost - current_price) / avg_cost
                return {
                    "action": "SELL_ALL",
                    "shares": position.shares_remaining,
                    "price_cents": current_price,
                    "reason": (
                        f"Universal stop: {current_price}¢ is -{loss_pct:.0%} from "
                        f"avg {avg_cost:.0f}¢ (Q{state.quarter})"
                    ),
                }

        if not position.capital_recovered:
            if gain_multiple >= TIER_CLASSIC_CAPITAL_RECOVERY_MULT:
                shares_to_sell = max(1, int(position.shares_remaining * TIER_CLASSIC_CAPITAL_RECOVERY_SELL_PCT))
                return {
                    "action": "SELL_PARTIAL",
                    "shares": shares_to_sell,
                    "price_cents": current_price,
                    "reason": f"Capital recovery: {gain_multiple:.1f}x (sell {TIER_CLASSIC_CAPITAL_RECOVERY_SELL_PCT:.0%})",
                    "mark_capital_recovered": True,
                }
        else:
            if gain_multiple >= TIER_CLASSIC_HOUSE_MONEY_1_MULT and not position.house_money_1_hit:
                shares_to_sell = max(1, int(position.shares_remaining * TIER_CLASSIC_HOUSE_MONEY_1_SELL_PCT))
                return {
                    "action": "SELL_PARTIAL",
                    "shares": shares_to_sell,
                    "price_cents": current_price,
                    "reason": f"House money 1: {gain_multiple:.1f}x",
                    "mark_house_money_1": True,
                }

            if gain_multiple >= TIER_CLASSIC_HOUSE_MONEY_2_MULT and not position.house_money_2_hit:
                shares_to_sell = max(1, int(position.shares_remaining * TIER_CLASSIC_HOUSE_MONEY_2_SELL_PCT))
                return {
                    "action": "SELL_PARTIAL",
                    "shares": shares_to_sell,
                    "price_cents": current_price,
                    "reason": f"House money 2: {gain_multiple:.1f}x",
                    "mark_house_money_2": True,
                }

            if current_price >= TIER_CLASSIC_LATE_GAME_PRICE_CENTS and state.quarter == 4 and state.time_remaining_seconds < 180:
                shares_to_sell = max(1, int(position.shares_remaining * TIER_CLASSIC_LATE_GAME_SELL_PCT))
                return {
                    "action": "SELL_PARTIAL",
                    "shares": shares_to_sell,
                    "price_cents": current_price,
                    "reason": f"Late game lock: {current_price}¢ with {state.time_remaining_seconds}s left",
                }

            if position.highest_price_cents > 0:
                drop_from_peak = (position.highest_price_cents - current_price) / position.highest_price_cents
                if drop_from_peak >= TIER_CLASSIC_TRAILING_STOP_PCT:
                    return {
                        "action": "SELL_ALL",
                        "shares": position.shares_remaining,
                        "price_cents": current_price,
                        "reason": f"Trailing stop: {drop_from_peak:.0%} from peak of {position.highest_price_cents}¢",
                    }

        if position.current_mode == GameMode.DEFENSIVE:
            if state.quarter >= 4:
                total_value = position.current_value_cents(current_price)
                if total_value < position.total_cost_cents * TIER_CLASSIC_DEFENSIVE_HARD_FLOOR_PCT:
                    return {
                        "action": "SELL_ALL",
                        "shares": position.shares_remaining,
                        "price_cents": current_price,
                        "reason": (
                            f"Hard floor: value {total_value}¢ < {TIER_CLASSIC_DEFENSIVE_HARD_FLOOR_PCT:.0%} "
                            f"of invested {position.total_cost_cents}¢"
                        ),
                    }

            if position.highest_price_cents > 0 and current_price > position.avg_cost_cents * 0.5 and state.momentum_score > 0.3:
                return {
                    "action": "SELL_ALL",
                    "shares": position.shares_remaining,
                    "price_cents": current_price,
                    "reason": f"Defensive exit: selling into strength at {current_price}¢ (momentum={state.momentum_score:.2f})",
                }

        return None

    def update_bankroll(self, new_bankroll_cents: int):
        self.bankroll_cents = new_bankroll_cents
