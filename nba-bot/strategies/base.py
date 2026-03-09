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
        current_price = state.kalshi_yes_ask or state.kalshi_last_price or 0
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
        if state.kalshi_yes_ask is None:
            return False

        # Must have Kalshi market matched
        if not state.kalshi_market_ticker:
            return False

        # Market must be open
        if state.kalshi_market_status not in ("open", "active", ""):
            return False

        # No trading in final 2 minutes
        if state.quarter == 4 and state.time_remaining_seconds < NO_TRADE_FINAL_MINUTES_SEC:
            return False

        return True

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
            team=state.favorite,  # Usually betting on the favorite
            strategy=self.name,
            entry_number=entry_number,
            kalshi_price_cents=state.kalshi_yes_ask or 0,
            fair_value=state.fair_value_home,
            edge=state.edge_conservative,
            deficit_vs_spread=state.deficit_vs_spread,
            price_drop_pct=state.price_drop_from_tipoff,
            pre_game_spread=state.opening_spread,
            quarter=state.quarter,
            time_remaining_seconds=state.time_remaining_seconds,
            momentum_score=state.momentum_score,
            confidence=confidence,
            suggested_shares=suggested_shares,
            suggested_cost_cents=suggested_cost_cents,
            budget_source=budget_source,
            orderbook_depth=state.kalshi_book_depth,
            bid_ask_spread_cents=state.kalshi_bid_ask_spread,
            reason=reason,
        )
