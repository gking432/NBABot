"""
Base strategy class.
Shared logic for all three strategies: mode management, position lookups, signal building.
"""
import logging
from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import datetime

from core.models import (
    LiveGameState, EntrySignal, Position, GameMode,
    GameStatus, Strategy, PositionStatus
    , ContractSide
)

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """
    Abstract base for all strategies.
    Subclasses implement check_entry() and check_exit().
    """

    def __init__(self, name: Strategy, positions: dict):
        self.name = name
        # Shared positions dict: {game_id: Position}
        # Managed by PositionManager, passed in by reference
        self.positions = positions
        self.contract_side = ContractSide.FAVORITE_YES

    @abstractmethod
    def check_entry(self, state: LiveGameState) -> Optional[EntrySignal]:
        """Check if entry conditions are met. Returns signal or None."""
        pass

    @abstractmethod
    def check_exit(self, state: LiveGameState, position: Position) -> Optional[dict]:
        """
        Check if any exit condition is met.
        Returns dict with {action, shares, reason} or None.
        """
        pass

    # ─────────────────────────────────────────
    # Shared Helpers
    # ─────────────────────────────────────────

    def get_position_for_game(self, game_id: str) -> Optional[Position]:
        """Get our active position in this game (if any) for this strategy."""
        pos = self.positions.get(game_id)
        if pos and pos.is_active:
            return pos
        return None

    def has_position(self, game_id: str) -> bool:
        """Do we have any position (active or not) in this game?"""
        return game_id in self.positions

    def determine_game_mode(self, state: LiveGameState, position: Position) -> GameMode:
        """
        Determine the current game mode based on quarter and position status.
        This governs what actions are allowed.
        """
        from core.config import NEUTRAL_MODE_Q3_WINDOW_SEC

        # Q1-Q2: always offensive
        if state.is_first_half:
            return GameMode.OFFENSIVE

        # Halftime: keep whatever mode we were in
        if state.game_status == GameStatus.HALFTIME:
            return position.current_mode

        # Q3: first 6 minutes = neutral, then potentially defensive
        if state.quarter == 3:
            # Time elapsed in Q3 = 720 - time_remaining
            q3_elapsed = 720 - state.time_remaining_seconds
            if q3_elapsed < NEUTRAL_MODE_Q3_WINDOW_SEC:
                return GameMode.NEUTRAL

        # Late Q3 or Q4: defensive if underwater
        current_price = self.get_current_price(state) or 0
        if current_price > 0 and position.current_return_pct(current_price) < 0:
            return GameMode.DEFENSIVE

        # Late game but profitable: stay neutral (exits handled by house money system)
        return GameMode.NEUTRAL

    def is_game_tradeable(self, state: LiveGameState) -> bool:
        """Basic checks that apply to all strategies."""
        from core.config import NO_TRADE_FINAL_MINUTES_SEC

        # Must be live
        if state.game_status != GameStatus.LIVE:
            return False

        # Must have Kalshi data
        if self.get_entry_price(state) is None:
            return False

        # Must have Kalshi market matched
        if not self.get_kalshi_ticker(state):
            return False

        # Market must be open
        if self.get_market_status(state) not in ("open", "active", ""):
            return False

        # No trading in final 2 minutes
        if state.quarter == 4 and state.time_remaining_seconds < NO_TRADE_FINAL_MINUTES_SEC:
            return False

        return True

    def get_contract_side(self) -> ContractSide:
        return self.contract_side

    def get_team(self, state: LiveGameState) -> str:
        return state.get_team_for_side(self.contract_side)

    def get_kalshi_ticker(self, state: LiveGameState) -> Optional[str]:
        return state.get_ticker_for_side(self.contract_side)

    def get_entry_price(self, state: LiveGameState) -> Optional[int]:
        return state.get_ask_for_side(self.contract_side)

    def get_current_price(self, state: LiveGameState) -> Optional[int]:
        return state.get_ask_for_side(self.contract_side) or state.get_last_price_for_side(self.contract_side)

    def get_book_depth(self, state: LiveGameState) -> int:
        return state.get_book_depth_for_side(self.contract_side)

    def get_bid_ask_spread(self, state: LiveGameState) -> int:
        return state.get_bid_ask_spread_for_side(self.contract_side)

    def get_market_status(self, state: LiveGameState) -> str:
        return state.get_market_status_for_side(self.contract_side)

    def get_fair_value(self, state: LiveGameState) -> Optional[float]:
        return state.get_fair_value_for_side(self.contract_side)

    def get_edge(self, state: LiveGameState) -> Optional[float]:
        return state.get_edge_for_side(self.contract_side)

    def get_price_drop(self, state: LiveGameState) -> float:
        return state.get_price_drop_from_tipoff_for_side(self.contract_side)

    def build_signal(
        self,
        state: LiveGameState,
        entry_number: int,
        suggested_shares: int,
        suggested_cost_cents: int,
        budget_source: str,
        confidence: int,
        reason: str,
    ) -> EntrySignal:
        """Create an EntrySignal with all context filled in."""
        return EntrySignal(
            game_id=state.game_id_espn,
            team=self.get_team(state),
            strategy=self.name,
            kalshi_ticker=self.get_kalshi_ticker(state) or "",
            contract_side=self.contract_side,
            entry_number=entry_number,
            kalshi_price_cents=self.get_entry_price(state) or 0,
            fair_value=self.get_fair_value(state),
            edge=self.get_edge(state),
            deficit_vs_spread=state.deficit_vs_spread,
            price_drop_pct=self.get_price_drop(state),
            pre_game_spread=state.opening_spread,
            quarter=state.quarter,
            time_remaining_seconds=state.time_remaining_seconds,
            momentum_score=state.momentum_score,
            confidence=confidence,
            suggested_shares=suggested_shares,
            suggested_cost_cents=suggested_cost_cents,
            budget_source=budget_source,
            orderbook_depth=self.get_book_depth(state),
            bid_ask_spread_cents=self.get_bid_ask_spread(state),
            reason=reason,
        )
