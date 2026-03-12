"""
Settlement-only strategy variants.
Reuse entry logic from base strategies, but never exit early.
"""
from typing import Optional

from core.models import LiveGameState, Position, Strategy
from strategies.conservative import ConservativeStrategy
from strategies.tiered import TieredStrategy
from strategies.tiered_classic import TieredClassicStrategy


class ConservativeHoldStrategy(ConservativeStrategy):
    def __init__(self, positions: dict, bankroll_cents: int):
        super().__init__(positions, bankroll_cents, strategy=Strategy.CONSERVATIVE_HOLD)

    def check_exit(self, state: LiveGameState, position: Position) -> Optional[dict]:
        return None


class TieredHoldStrategy(TieredStrategy):
    def __init__(self, positions: dict, bankroll_cents: int):
        super().__init__(positions, bankroll_cents, strategy=Strategy.TIERED_HOLD)

    def check_exit(self, state: LiveGameState, position: Position) -> Optional[dict]:
        return None


class TieredClassicHoldStrategy(TieredClassicStrategy):
    def __init__(self, positions: dict, bankroll_cents: int):
        super().__init__(positions, bankroll_cents, strategy=Strategy.TIERED_CLASSIC_HOLD)

    def check_exit(self, state: LiveGameState, position: Position) -> Optional[dict]:
        return None
