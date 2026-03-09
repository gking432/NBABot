"""
Position Manager.
Handles opening positions, multi-entry tracking, executing exits,
injury responses, and settlement.
"""
import logging
from typing import Optional, Dict, List
from datetime import datetime

from core.models import (
    Position, EntryRecord, ExitRecord, EntrySignal, TradeRecord,
    LiveGameState, GameMode, PositionStatus, TradeAction,
    Strategy, InjuryEvent, InjurySeverity
)
from core.database import Database
from data.injury_detector import InjuryDetector

logger = logging.getLogger(__name__)


class PositionManager:
    """
    Manages all positions across all strategies.
    Handles entry execution, exit execution, injury response, and settlement.
    """

    def __init__(self, db: Database, injury_detector: InjuryDetector):
        self.db = db
        self.injury_detector = injury_detector

        # Active positions by strategy: {game_id: Position}
        self.conservative_positions: Dict[str, Position] = {}
        self.tiered_positions: Dict[str, Position] = {}
        self.tiered_classic_positions: Dict[str, Position] = {}
        self.heavy_favorite_positions: Dict[str, Position] = {}

        self._entry_locks: set = set()

        # Strategy bankrolls (in cents)
        self.bankrolls: Dict[Strategy, int] = {
            Strategy.CONSERVATIVE: 0,
            Strategy.TIERED: 0,
            Strategy.TIERED_CLASSIC: 0,
            Strategy.HEAVY_FAVORITE: 0,
        }

    def initialize_bankrolls(self, total_bankroll_cents: int):
        """
        Set up bankrolls: start from initial allocation, then replay all
        historical trades to reconstruct current balances.
        Also restores any active positions from the database.
        """
        from core.config import (
            CONSERVATIVE_BANKROLL_PCT, TIERED_BANKROLL_PCT,
            TIERED_CLASSIC_BANKROLL_PCT, HEAVY_FAVORITE_BANKROLL_PCT
        )
        self.bankrolls[Strategy.CONSERVATIVE] = int(total_bankroll_cents * CONSERVATIVE_BANKROLL_PCT)
        self.bankrolls[Strategy.TIERED] = int(total_bankroll_cents * TIERED_BANKROLL_PCT)
        self.bankrolls[Strategy.TIERED_CLASSIC] = int(total_bankroll_cents * TIERED_CLASSIC_BANKROLL_PCT)
        self.bankrolls[Strategy.HEAVY_FAVORITE] = int(total_bankroll_cents * HEAVY_FAVORITE_BANKROLL_PCT)

        logger.info(
            f"Base bankrolls: Conservative={self.bankrolls[Strategy.CONSERVATIVE]}¢, "
            f"Tiered={self.bankrolls[Strategy.TIERED]}¢, "
            f"TieredClassic={self.bankrolls[Strategy.TIERED_CLASSIC]}¢, "
            f"HeavyFavorite={self.bankrolls[Strategy.HEAVY_FAVORITE]}¢"
        )

        self._replay_trade_history()
        self._restore_active_positions()

        logger.info(
            f"Reconstructed bankrolls: Conservative={self.bankrolls[Strategy.CONSERVATIVE]}¢, "
            f"Tiered={self.bankrolls[Strategy.TIERED]}¢, "
            f"TieredClassic={self.bankrolls[Strategy.TIERED_CLASSIC]}¢, "
            f"HeavyFavorite={self.bankrolls[Strategy.HEAVY_FAVORITE]}¢"
        )

    def _replay_trade_history(self):
        """Replay all historical trades to reconstruct accurate bankrolls."""
        trades = self.db.get_all_trades_for_replay()
        if not trades:
            logger.info("No trade history to replay — using initial bankrolls")
            return

        trade_count = 0
        for t in trades:
            strategy_str = t.get("strategy", "")
            try:
                strategy = Strategy(strategy_str)
            except ValueError:
                logger.warning(f"Unknown strategy in trade history: {strategy_str}")
                continue

            action = t.get("action", "")
            total_cents = t.get("total_cents", 0) or 0

            if action == "BUY":
                self.bankrolls[strategy] -= total_cents
            elif action in ("SELL_PARTIAL", "SELL_ALL", "SETTLED_WIN"):
                self.bankrolls[strategy] += total_cents
            # SETTLED_LOSS has total_cents=0, no bankroll change needed

            trade_count += 1

        logger.info(f"Replayed {trade_count} trades to reconstruct bankrolls")

    def _restore_active_positions(self):
        """Reload active positions from the database so they survive restarts."""
        active = self.db.get_active_positions_full()
        if not active:
            logger.info("No active positions to restore")
            return

        restored = 0
        for pos_data in active:
            try:
                strategy = Strategy(pos_data["strategy"])
            except ValueError:
                continue

            position = Position(
                position_id=pos_data["position_id"],
                game_id=pos_data["game_id"],
                kalshi_ticker=pos_data.get("kalshi_ticker", ""),
                team=pos_data.get("team", ""),
                strategy=strategy,
            )

            # Rebuild entries from BUY trades
            buy_trades = [t for t in pos_data.get("trades", []) if t.get("action") == "BUY"]
            for t in buy_trades:
                entry = EntryRecord(
                    entry_number=t.get("entry_number", 1) or 1,
                    quarter=t.get("game_quarter", 0),
                    time_remaining_seconds=t.get("game_time_remaining", 0),
                    price_cents=t.get("price_cents", 0),
                    shares=t.get("shares", 0),
                    cost_cents=t.get("total_cents", 0),
                    budget_source="GAME_BUDGET",
                    reason=t.get("reason", ""),
                )
                position.add_entry(entry)

            # Rebuild exits from SELL trades
            sell_trades = [t for t in pos_data.get("trades", [])
                          if t.get("action") in ("SELL_PARTIAL", "SELL_ALL")]
            for t in sell_trades:
                exit_record = ExitRecord(
                    price_cents=t.get("price_cents", 0),
                    shares=t.get("shares", 0),
                    proceeds_cents=t.get("total_cents", 0),
                    reason=t.get("reason", ""),
                    game_quarter=t.get("game_quarter", 0),
                    game_time_remaining=t.get("game_time_remaining", 0),
                    pnl_cents=t.get("pnl_cents", 0) or 0,
                )
                position.add_exit(exit_record)

            # Restore state flags from DB
            position.capital_recovered = bool(pos_data.get("capital_recovered", False))
            position.capital_recovered_amount_cents = pos_data.get("capital_recovered_amount", 0) or 0
            position.highest_price_cents = pos_data.get("highest_price_cents", 0) or 0

            status_str = pos_data.get("status", "ACTIVE")
            try:
                position.status = PositionStatus(status_str)
            except ValueError:
                position.status = PositionStatus.ACTIVE

            mode_str = pos_data.get("current_mode", "OFFENSIVE")
            try:
                position.current_mode = GameMode(mode_str)
            except ValueError:
                position.current_mode = GameMode.OFFENSIVE

            # Place into the correct strategy dict (skip if duplicate game_id)
            positions_dict = self.get_positions_dict(strategy)
            if position.game_id in positions_dict:
                logger.warning(
                    f"Skipping duplicate position {position.position_id} for "
                    f"{strategy.value} game {position.game_id} — already restored"
                )
                continue
            positions_dict[position.game_id] = position
            restored += 1

            logger.info(
                f"Restored position: {strategy.value} | {position.team} | "
                f"{position.shares_remaining} shares @ avg {position.avg_cost_cents:.1f}¢"
            )

        logger.info(f"Restored {restored} active positions from database")

    def get_positions_dict(self, strategy: Strategy) -> Dict[str, Position]:
        """Get the positions dict for a strategy (used by strategy classes)."""
        if strategy == Strategy.CONSERVATIVE:
            return self.conservative_positions
        elif strategy == Strategy.TIERED:
            return self.tiered_positions
        elif strategy == Strategy.TIERED_CLASSIC:
            return self.tiered_classic_positions
        elif strategy == Strategy.HEAVY_FAVORITE:
            return self.heavy_favorite_positions
        return {}

    def get_all_active_positions(self) -> List[Position]:
        """Get all active positions across all strategies."""
        all_pos = []
        for positions in [self.conservative_positions, self.tiered_positions,
                          self.tiered_classic_positions, self.heavy_favorite_positions]:
            all_pos.extend(p for p in positions.values() if p.is_active)
        return all_pos

    def count_positions(self, strategy: Strategy) -> int:
        """Count active positions for a strategy."""
        positions = self.get_positions_dict(strategy)
        return sum(1 for p in positions.values() if p.is_active)

    # ─────────────────────────────────────────
    # Entry Execution
    # ─────────────────────────────────────────

    def execute_entry(
        self,
        signal: EntrySignal,
        state: LiveGameState,
        fill_price_cents: int,
    ) -> Optional[Position]:
        """
        Execute an entry signal.
        For paper trading, fill_price_cents = signal.kalshi_price_cents.
        For live trading, it's the actual fill price.
        """
        from core.config import MAX_LIQUIDITY_CONSUMPTION_PCT

        entry_key = (signal.strategy.value, signal.game_id, signal.entry_number)
        if entry_key in self._entry_locks:
            logger.warning(
                f"Rapid duplicate blocked: {signal.strategy.value} "
                f"Entry {signal.entry_number} game {signal.game_id}"
            )
            return None
        self._entry_locks.add(entry_key)

        if signal.entry_number == 1:
            if self.db.has_active_position(signal.strategy.value, signal.game_id):
                logger.warning(
                    f"DB duplicate blocked: {signal.strategy.value} already has "
                    f"active position in game {signal.game_id}"
                )
                return None

        # Safety: check liquidity
        if state.kalshi_book_depth > 0:
            consumption = signal.suggested_shares / state.kalshi_book_depth
            if consumption > MAX_LIQUIDITY_CONSUMPTION_PCT:
                logger.warning(
                    f"Would consume {consumption:.0%} of book depth — reducing size"
                )
                signal.suggested_shares = int(state.kalshi_book_depth * MAX_LIQUIDITY_CONSUMPTION_PCT)
                signal.suggested_cost_cents = signal.suggested_shares * fill_price_cents

        if signal.suggested_shares < 1:
            logger.warning("Order too small after liquidity adjustment — skipping")
            return None

        positions = self.get_positions_dict(signal.strategy)
        game_id = signal.game_id

        if game_id in positions:
            position = positions[game_id]
            if signal.entry_number == 1:
                logger.warning(
                    f"Duplicate Entry 1 blocked: {signal.strategy.value} already has "
                    f"position in game {game_id} ({signal.team}) "
                    f"[status={position.status.value}]"
                )
                return None
            if not position.is_active:
                logger.warning(
                    f"Entry {signal.entry_number} blocked: position for "
                    f"{signal.strategy.value} game {game_id} is {position.status.value}"
                )
                return None
            if signal.entry_number <= position.entry_count:
                logger.warning(
                    f"Duplicate Entry {signal.entry_number} blocked: "
                    f"{signal.strategy.value} game {game_id} already has "
                    f"{position.entry_count} entries"
                )
                return None
        else:
            if signal.entry_number != 1:
                logger.warning(
                    f"Entry {signal.entry_number} blocked: no position exists for "
                    f"{signal.strategy.value} game {game_id}"
                )
                return None
            position = Position(
                game_id=game_id,
                kalshi_ticker=state.kalshi_market_ticker or "",
                team=signal.team,
                strategy=signal.strategy,
            )
            positions[game_id] = position

        # Record the entry
        entry = EntryRecord(
            entry_number=signal.entry_number,
            quarter=state.quarter,
            time_remaining_seconds=state.time_remaining_seconds,
            price_cents=fill_price_cents,
            shares=signal.suggested_shares,
            cost_cents=signal.suggested_shares * fill_price_cents,
            budget_source=signal.budget_source,
            reason=signal.reason,
        )
        position.add_entry(entry)

        # Deduct from bankroll
        self.bankrolls[signal.strategy] -= entry.cost_cents

        # Log trade
        trade = TradeRecord(
            position_id=position.position_id,
            game_id=game_id,
            kalshi_ticker=position.kalshi_ticker,
            team=signal.team,
            strategy=signal.strategy,
            action=TradeAction.BUY,
            entry_number=signal.entry_number,
            price_cents=fill_price_cents,
            shares=signal.suggested_shares,
            total_cents=entry.cost_cents,
            reason=signal.reason,
            game_quarter=state.quarter,
            game_time_remaining_seconds=state.time_remaining_seconds,
            game_score_home=state.home_score,
            game_score_away=state.away_score,
            deficit_vs_spread=state.deficit_vs_spread,
            fair_value=state.fair_value_home,
            edge=state.edge_conservative,
            price_drop_pct=state.price_drop_from_tipoff,
            orderbook_depth=state.kalshi_book_depth,
            game_mode=position.current_mode,
        )
        self.db.log_trade(trade)

        # Save position to DB
        self.db.save_position(position)

        logger.info(
            f"ENTRY {signal.entry_number} executed: {signal.strategy.value} | "
            f"{signal.team} | {signal.suggested_shares} shares @ {fill_price_cents}¢ | "
            f"Total cost: {entry.cost_cents}¢ | Avg cost: {position.avg_cost_cents:.1f}¢"
        )

        return position

    # ─────────────────────────────────────────
    # Exit Execution
    # ─────────────────────────────────────────

    def execute_exit(
        self,
        position: Position,
        state: LiveGameState,
        exit_info: dict,
    ):
        """
        Execute an exit (partial or full).
        exit_info: {action, shares, price_cents, reason, mark_capital_recovered?, ...}
        """
        shares = exit_info["shares"]
        price_cents = exit_info["price_cents"]
        proceeds = shares * price_cents
        reason = exit_info["reason"]

        # Calculate P&L for this exit
        cost_of_shares = int(shares * position.avg_cost_cents)
        pnl = proceeds - cost_of_shares

        # Record the exit
        exit_record = ExitRecord(
            price_cents=price_cents,
            shares=shares,
            proceeds_cents=proceeds,
            reason=reason,
            game_quarter=state.quarter,
            game_time_remaining=state.time_remaining_seconds,
            pnl_cents=pnl,
        )
        position.add_exit(exit_record)

        # Handle capital recovery flag
        if exit_info.get("mark_capital_recovered"):
            position.capital_recovered = True
            position.capital_recovered_amount_cents = proceeds
            position.status = PositionStatus.CAPITAL_RECOVERED

        # Handle exit stage flags
        if exit_info.get("mark_house_money_1"):
            position.house_money_1_hit = True
        if exit_info.get("mark_house_money_2"):
            position.house_money_2_hit = True
        if exit_info.get("mark_q3_shaved"):
            position.q3_shaved = True

        # Update status if fully closed
        if position.shares_remaining <= 0:
            if pnl >= 0:
                position.status = PositionStatus.CLOSED_TP
            else:
                position.status = PositionStatus.CLOSED_SL

        # Add proceeds back to bankroll
        self.bankrolls[position.strategy] += proceeds

        # Determine trade action
        if exit_info["action"] == "SELL_ALL" or position.shares_remaining <= 0:
            action = TradeAction.SELL_ALL
        else:
            action = TradeAction.SELL_PARTIAL

        # Log trade
        trade = TradeRecord(
            position_id=position.position_id,
            game_id=position.game_id,
            kalshi_ticker=position.kalshi_ticker,
            team=position.team,
            strategy=position.strategy,
            action=action,
            price_cents=price_cents,
            shares=shares,
            total_cents=proceeds,
            pnl_cents=pnl,
            reason=reason,
            game_quarter=state.quarter,
            game_time_remaining_seconds=state.time_remaining_seconds,
            game_score_home=state.home_score,
            game_score_away=state.away_score,
            deficit_vs_spread=state.deficit_vs_spread,
            fair_value=state.fair_value_home,
            edge=state.edge_conservative,
            price_drop_pct=state.price_drop_from_tipoff,
            orderbook_depth=state.kalshi_book_depth,
            game_mode=position.current_mode,
        )
        self.db.log_trade(trade)
        self.db.save_position(position)

        logger.info(
            f"EXIT: {position.strategy.value} | {position.team} | "
            f"{shares} shares @ {price_cents}¢ | P&L: {pnl:+}¢ | "
            f"Reason: {reason} | Remaining: {position.shares_remaining}"
        )

    # ─────────────────────────────────────────
    # Settlement
    # ─────────────────────────────────────────

    def settle_game(self, game_id: str, winning_team: str):
        """
        Handle game settlement. Contracts pay $1.00 (100¢) for winners, $0 for losers.
        """
        for positions_dict in [self.conservative_positions,
                               self.tiered_positions,
                               self.tiered_classic_positions,
                               self.heavy_favorite_positions]:

            if game_id not in positions_dict:
                continue

            position = positions_dict[game_id]
            if not position.is_active:
                continue

            from data.team_names import teams_match

            if teams_match(position.team, winning_team):
                # WIN — each remaining share pays 100¢
                proceeds = position.shares_remaining * 100
                pnl = proceeds - int(position.shares_remaining * position.avg_cost_cents)

                exit_record = ExitRecord(
                    price_cents=100,
                    shares=position.shares_remaining,
                    proceeds_cents=proceeds,
                    reason="SETTLEMENT_WIN",
                    pnl_cents=pnl,
                )
                position.add_exit(exit_record)
                position.status = PositionStatus.CLOSED_SETTLED_WIN

                self.bankrolls[position.strategy] += proceeds

                trade = TradeRecord(
                    position_id=position.position_id,
                    game_id=game_id,
                    kalshi_ticker=position.kalshi_ticker,
                    team=position.team,
                    strategy=position.strategy,
                    action=TradeAction.SETTLED_WIN,
                    price_cents=100,
                    shares=position.shares_remaining,
                    total_cents=proceeds,
                    pnl_cents=pnl,
                    reason="Game settled - team won",
                )
                self.db.log_trade(trade)

                logger.info(
                    f"SETTLEMENT WIN: {position.strategy.value} | {position.team} | "
                    f"{position.shares_remaining} shares @ 100¢ | P&L: {pnl:+}¢"
                )

            else:
                # LOSS — shares worth nothing
                cost = int(position.shares_remaining * position.avg_cost_cents)
                pnl = -cost

                exit_record = ExitRecord(
                    price_cents=0,
                    shares=position.shares_remaining,
                    proceeds_cents=0,
                    reason="SETTLEMENT_LOSS",
                    pnl_cents=pnl,
                )
                position.add_exit(exit_record)
                position.status = PositionStatus.CLOSED_SETTLED_LOSS

                trade = TradeRecord(
                    position_id=position.position_id,
                    game_id=game_id,
                    kalshi_ticker=position.kalshi_ticker,
                    team=position.team,
                    strategy=position.strategy,
                    action=TradeAction.SETTLED_LOSS,
                    price_cents=0,
                    shares=position.shares_remaining,
                    total_cents=0,
                    pnl_cents=pnl,
                    reason="Game settled - team lost",
                )
                self.db.log_trade(trade)

                logger.info(
                    f"SETTLEMENT LOSS: {position.strategy.value} | {position.team} | "
                    f"{position.shares_remaining} shares → $0 | P&L: {pnl}¢"
                )

            self.db.save_position(position)

    # ─────────────────────────────────────────
    # Injury Response
    # ─────────────────────────────────────────

    def handle_injury(self, injury: InjuryEvent, state: LiveGameState):
        """
        Respond to a detected injury based on team depth and player importance.
        """
        team = injury.team
        player = injury.player_name

        # Find affected positions across all strategies
        for positions_dict, strategy_name in [
            (self.conservative_positions, "conservative"),
            (self.tiered_positions, "tiered"),
            (self.tiered_classic_positions, "tiered_classic"),
            (self.heavy_favorite_positions, "heavy_favorite"),
        ]:
            if state.game_id_espn not in positions_dict:
                continue

            position = positions_dict[state.game_id_espn]
            if not position.is_active:
                continue

            # Only care about injuries on OUR team
            from data.team_names import teams_match
            if not teams_match(team, position.team):
                # Opponent injury — good for us, no action
                continue

            # Determine team depth
            team_depth = self.injury_detector.get_team_depth(team)

            if team_depth == "SINGLE_STAR":
                # ─── SINGLE STAR INJURED: reduce position ───
                if self.injury_detector.is_star_player(team, player):
                    logger.warning(
                        f"SINGLE-STAR INJURY: {player} on {team} — reducing position"
                    )

                    # Sell 50% immediately
                    current_price = state.kalshi_yes_ask or state.kalshi_last_price or 1
                    shares_to_sell = position.shares_remaining // 2

                    if shares_to_sell > 0:
                        self.execute_exit(position, state, {
                            "action": "SELL_PARTIAL",
                            "shares": shares_to_sell,
                            "price_cents": current_price,
                            "reason": f"Injury response: {player} (single-star team) — sell 50%",
                        })

                    # If confirmed out, sell remaining
                    if injury.confirmed:
                        if position.shares_remaining > 0:
                            self.execute_exit(position, state, {
                                "action": "SELL_ALL",
                                "shares": position.shares_remaining,
                                "price_cents": current_price,
                                "reason": f"Injury confirmed: {player} OUT — sell all",
                            })

                    position.status = PositionStatus.CLOSED_INJURY

            else:
                # ─── MULTI-STAR TEAM: shift to defensive mode ───
                if self.injury_detector.is_star_player(team, player):
                    logger.warning(
                        f"MULTI-STAR INJURY: {player} on {team} — shifting to defensive mode"
                    )
                    position.current_mode = GameMode.DEFENSIVE
                    self.db.save_position(position)

                    # Don't sell — just change mode. The exit logic will handle it.

            # Log the injury response
            injury.position_id = position.position_id
            injury.action_taken = (
                f"Position {position.position_id}: mode → {position.current_mode.value}"
            )
            self.db.log_injury_event(injury)
