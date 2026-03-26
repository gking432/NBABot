"""
Flip strategy variants.
These keep the parent entry logic but trade YES on the underdog contract.
"""
from typing import Optional

from core.models import LiveGameState, Position, Strategy, ContractSide
from strategies.conservative import ConservativeStrategy
from strategies.tiered import TieredStrategy


class ConservativeHoldFlipStrategy(ConservativeStrategy):
    def __init__(self, positions: dict, bankroll_cents: int):
        super().__init__(positions, bankroll_cents, strategy=Strategy.CONSERVATIVE_HOLD_FLIP)
        self.contract_side = ContractSide.UNDERDOG_YES

    def check_exit(self, state: LiveGameState, position: Position) -> Optional[dict]:
        return None


class TieredHoldFlipStrategy(TieredStrategy):
    def __init__(self, positions: dict, bankroll_cents: int):
        super().__init__(positions, bankroll_cents, strategy=Strategy.TIERED_HOLD_FLIP)
        self.contract_side = ContractSide.UNDERDOG_YES

    def check_exit(self, state: LiveGameState, position: Position) -> Optional[dict]:
        return None


class TieredFlipStrategy(TieredStrategy):
    def __init__(self, positions: dict, bankroll_cents: int):
        super().__init__(positions, bankroll_cents, strategy=Strategy.TIERED_FLIP)
        self.contract_side = ContractSide.UNDERDOG_YES
