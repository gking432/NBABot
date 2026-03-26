"""
All data models for the trading bot.
Every object that flows through the system is defined here.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Tuple
from enum import Enum
import uuid


class GameStatus(str, Enum):
    PRE = "pre"
    LIVE = "live"
    HALFTIME = "halftime"
    FINAL = "final"


class Strategy(str, Enum):
    CONSERVATIVE = "CONSERVATIVE"
    TIERED = "TIERED"
    TIERED_CLASSIC = "TIERED_CLASSIC"
    GARBAGE_TIME = "GARBAGE_TIME"
    CONSERVATIVE_HOLD = "CONSERVATIVE_HOLD"
    CONSERVATIVE_HOLD_FLIP = "CONSERVATIVE_HOLD_FLIP"
    TIERED_HOLD = "TIERED_HOLD"
    TIERED_HOLD_FLIP = "TIERED_HOLD_FLIP"
    TIERED_CLASSIC_HOLD = "TIERED_CLASSIC_HOLD"
    TIERED_FLIP = "TIERED_FLIP"
    PULSE = "PULSE"


# DB / exports may still use these for the strategy that is now Strategy.GARBAGE_TIME (Bounceback).
BOUNCEBACK_STRATEGY_DB_ALIASES: Tuple[str, ...] = (
    "HEAVY_FAVORITE",
    "Heavy Favorite",
    "heavy_favorite",
    "Heavy_Favorite",
    "HEAVY FAVORITE",
)


def strategy_from_stored_value(value: Optional[str]) -> Optional[Strategy]:
    """Map persisted DB strategy strings to enum (handles renames)."""
    if not value:
        return None
    v = value.strip()
    if v in BOUNCEBACK_STRATEGY_DB_ALIASES:
        return Strategy.GARBAGE_TIME
    if v.replace(" ", "_").upper() == "HEAVY_FAVORITE":
        return Strategy.GARBAGE_TIME
    try:
        return Strategy(v)
    except ValueError:
        return None


class GameMode(str, Enum):
    OFFENSIVE = "OFFENSIVE"      # Q1-Q2: all entries allowed, wide stops
    NEUTRAL = "NEUTRAL"          # Early Q3: hold, monitor, no entries
    DEFENSIVE = "DEFENSIVE"      # Late Q3-Q4 when underwater: sell into strength


class ContractSide(str, Enum):
    FAVORITE_YES = "FAVORITE_YES"
    UNDERDOG_YES = "UNDERDOG_YES"


class PositionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    CAPITAL_RECOVERED = "CAPITAL_RECOVERED"
    CLOSED_TP = "CLOSED_TP"                    # Closed via take profit
    CLOSED_SL = "CLOSED_SL"                    # Closed via stop loss
    CLOSED_DEFENSIVE = "CLOSED_DEFENSIVE"      # Closed in defensive mode
    CLOSED_SETTLED_WIN = "CLOSED_SETTLED_WIN"   # Game ended, team won
    CLOSED_SETTLED_LOSS = "CLOSED_SETTLED_LOSS" # Game ended, team lost
    CLOSED_INJURY = "CLOSED_INJURY"            # Closed due to injury


class TradeAction(str, Enum):
    BUY = "BUY"
    SELL_PARTIAL = "SELL_PARTIAL"
    SELL_ALL = "SELL_ALL"
    SETTLED_WIN = "SETTLED_WIN"
    SETTLED_LOSS = "SETTLED_LOSS"


class TeamDepth(str, Enum):
    SINGLE_STAR = "SINGLE_STAR"    # One dominant player
    MULTI_STAR = "MULTI_STAR"      # Two or three stars


class InjurySeverity(str, Enum):
    POTENTIAL = "POTENTIAL"        # Absence detected in play-by-play
    CONFIRMED = "CONFIRMED"        # Official NBA report says out


# ─────────────────────────────────────────────
# Core Data Objects
# ─────────────────────────────────────────────

@dataclass
class LiveGameState:
    """Everything we know about a single game at a point in time."""

    # Identifiers
    game_id_espn: str = ""
    game_id_nba: Optional[str] = None
    kalshi_event_ticker: Optional[str] = None
    kalshi_market_ticker: Optional[str] = None
    kalshi_yes_team: Optional[str] = None
    kalshi_favorite_ticker: Optional[str] = None
    kalshi_underdog_ticker: Optional[str] = None

    # Teams (canonical names from team_names.py)
    home_team: str = ""
    away_team: str = ""
    favorite: str = ""
    underdog: str = ""

    # Live Score
    home_score: int = 0
    away_score: int = 0
    quarter: int = 0                         # 1-4, 5+ = overtime
    time_remaining_seconds: int = 720        # seconds left in current quarter
    game_status: GameStatus = GameStatus.PRE

    # Pre-game
    start_time: Optional[str] = None         # ISO 8601 (e.g. "2026-03-15T23:30Z") — for PRE games

    # Spreads & Odds
    opening_spread: float = 0.0              # ESPN pre-game (e.g., -5.5 = home favored by 5.5)
    current_spread: Optional[float] = None   # Live from The Odds API
    fair_value_home: Optional[float] = None  # Vig-removed probability (0 to 1)
    fair_value_away: Optional[float] = None
    odds_last_updated: Optional[datetime] = None

    # Kalshi Market Data (ALL IN CENTS, 1-99)
    kalshi_yes_bid: Optional[int] = None
    kalshi_yes_ask: Optional[int] = None
    kalshi_last_price: Optional[int] = None
    kalshi_volume: int = 0
    kalshi_open_interest: int = 0
    kalshi_opening_price: Optional[int] = None   # First trade at market open
    kalshi_tipoff_price: Optional[int] = None     # Price when game tipped off
    kalshi_book_depth: int = 0                    # Contracts available in top 5 ask levels
    kalshi_bid_ask_spread: int = 0
    kalshi_market_status: str = ""                # "open", "closed", etc.
    kalshi_underdog_bid: Optional[int] = None
    kalshi_underdog_ask: Optional[int] = None
    kalshi_underdog_last_price: Optional[int] = None
    kalshi_underdog_volume: int = 0
    kalshi_underdog_open_interest: int = 0
    kalshi_underdog_opening_price: Optional[int] = None
    kalshi_underdog_tipoff_price: Optional[int] = None
    kalshi_underdog_book_depth: int = 0
    kalshi_underdog_bid_ask_spread: int = 0
    kalshi_underdog_market_status: str = ""

    # Derived Signals (calculated by aggregator)
    deficit_vs_spread: float = 0.0           # Always positive: how much worse than expected
    score_differential: int = 0              # From favorite's perspective (negative = losing)
    edge_conservative: Optional[float] = None  # fair_value - kalshi_ask/100
    price_drop_from_tipoff: float = 0.0      # (tipoff - current) / tipoff
    momentum_score: float = 0.0              # -1 to 1 from play-by-play

    # Timestamps
    last_score_update: Optional[datetime] = None
    last_kalshi_update: Optional[datetime] = None
    last_odds_update: Optional[datetime] = None

    @property
    def favorite_score(self) -> int:
        if self.favorite == self.home_team:
            return self.home_score
        return self.away_score

    @property
    def underdog_score(self) -> int:
        if self.underdog == self.home_team:
            return self.home_score
        return self.away_score

    @property
    def total_game_seconds_elapsed(self) -> int:
        """Total seconds elapsed in the game so far."""
        if self.quarter <= 0:
            return 0
        completed_quarters = max(0, self.quarter - 1)
        current_quarter_elapsed = 720 - self.time_remaining_seconds
        return (completed_quarters * 720) + current_quarter_elapsed

    @property
    def is_q1(self) -> bool:
        return self.quarter == 1

    @property
    def is_q2(self) -> bool:
        return self.quarter == 2

    @property
    def is_first_half(self) -> bool:
        return self.quarter in (1, 2)

    @property
    def is_second_half(self) -> bool:
        return self.quarter >= 3

    @property
    def is_overtime(self) -> bool:
        return self.quarter >= 5

    def get_ticker_for_side(self, side: ContractSide) -> Optional[str]:
        if side == ContractSide.UNDERDOG_YES:
            return self.kalshi_underdog_ticker
        return self.kalshi_favorite_ticker or self.kalshi_market_ticker

    def get_team_for_side(self, side: ContractSide) -> str:
        if side == ContractSide.UNDERDOG_YES:
            return self.underdog
        return self.favorite

    def get_ask_for_side(self, side: ContractSide) -> Optional[int]:
        if side == ContractSide.UNDERDOG_YES:
            return self.kalshi_underdog_ask
        return self.kalshi_yes_ask

    def get_bid_for_side(self, side: ContractSide) -> Optional[int]:
        if side == ContractSide.UNDERDOG_YES:
            return self.kalshi_underdog_bid
        return self.kalshi_yes_bid

    def get_last_price_for_side(self, side: ContractSide) -> Optional[int]:
        if side == ContractSide.UNDERDOG_YES:
            return self.kalshi_underdog_last_price
        return self.kalshi_last_price

    def get_book_depth_for_side(self, side: ContractSide) -> int:
        if side == ContractSide.UNDERDOG_YES:
            return self.kalshi_underdog_book_depth
        return self.kalshi_book_depth

    def get_bid_ask_spread_for_side(self, side: ContractSide) -> int:
        if side == ContractSide.UNDERDOG_YES:
            return self.kalshi_underdog_bid_ask_spread
        return self.kalshi_bid_ask_spread

    def get_market_status_for_side(self, side: ContractSide) -> str:
        if side == ContractSide.UNDERDOG_YES:
            return self.kalshi_underdog_market_status
        return self.kalshi_market_status

    def get_opening_price_for_side(self, side: ContractSide) -> Optional[int]:
        if side == ContractSide.UNDERDOG_YES:
            return self.kalshi_underdog_opening_price
        return self.kalshi_opening_price

    def get_tipoff_price_for_side(self, side: ContractSide) -> Optional[int]:
        if side == ContractSide.UNDERDOG_YES:
            return self.kalshi_underdog_tipoff_price
        return self.kalshi_tipoff_price

    def get_fair_value_for_side(self, side: ContractSide) -> Optional[float]:
        if side == ContractSide.UNDERDOG_YES:
            if self.underdog == self.home_team:
                return self.fair_value_home
            if self.underdog == self.away_team:
                return self.fair_value_away
            return self.fair_value_away
        if self.favorite == self.home_team:
            return self.fair_value_home
        if self.favorite == self.away_team:
            return self.fair_value_away
        return self.fair_value_home

    def get_edge_for_side(self, side: ContractSide) -> Optional[float]:
        ask = self.get_ask_for_side(side)
        fair_value = self.get_fair_value_for_side(side)
        if ask is None or fair_value is None:
            return None
        return fair_value - (ask / 100.0)

    def get_price_drop_from_tipoff_for_side(self, side: ContractSide) -> float:
        tipoff = self.get_tipoff_price_for_side(side)
        current = self.get_ask_for_side(side)
        if not tipoff or current is None or tipoff <= 0:
            return 0.0
        return max(0.0, (tipoff - current) / tipoff)


@dataclass
class EntryRecord:
    """A single entry into a position (there can be up to 4 per position)."""
    entry_number: int               # 1, 2, 3, or 4
    timestamp: datetime = field(default_factory=datetime.utcnow)
    quarter: int = 0
    time_remaining_seconds: int = 0
    price_cents: int = 0
    shares: int = 0
    cost_cents: int = 0             # price * shares
    budget_source: str = "GAME_BUDGET"  # or "NUCLEAR_RESERVE"
    reason: str = ""


@dataclass
class ExitRecord:
    """A single exit from a position (there can be many: partial sells, etc.)."""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    price_cents: int = 0
    shares: int = 0
    proceeds_cents: int = 0         # price * shares
    reason: str = ""                # "TP1", "TP2", "CAPITAL_RECOVERY", "HOUSE_MONEY_1",
                                    # "TRAILING_STOP", "DEFENSIVE_EXIT", "HARD_FLOOR",
                                    # "INJURY_EXIT", "SETTLEMENT"
    game_quarter: int = 0
    game_time_remaining: int = 0
    pnl_cents: int = 0              # profit/loss for this exit


@dataclass
class Position:
    """Tracks a complete position across all entries and exits."""
    position_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    game_id: str = ""
    kalshi_ticker: str = ""
    team: str = ""
    strategy: Strategy = Strategy.TIERED
    contract_side: ContractSide = ContractSide.FAVORITE_YES

    # Entry tracking
    entries: List[EntryRecord] = field(default_factory=list)
    entry_count: int = 0

    # Aggregated entry stats
    total_shares: int = 0
    total_cost_cents: int = 0

    # Budget tracking
    game_budget_used_cents: int = 0
    nuclear_budget_used_cents: int = 0

    # Exit tracking
    exits: List[ExitRecord] = field(default_factory=list)
    shares_remaining: int = 0
    total_proceeds_cents: int = 0

    # State
    status: PositionStatus = PositionStatus.ACTIVE
    capital_recovered: bool = False
    capital_recovered_amount_cents: int = 0
    highest_price_cents: int = 0     # For trailing stop
    current_mode: GameMode = GameMode.OFFENSIVE

    # Exit stages reached
    house_money_1_hit: bool = False  # 65¢ price target
    house_money_2_hit: bool = False  # 82¢ price target
    q3_shaved: bool = False          # Q3 early-lead shave fired

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    closed_at: Optional[datetime] = None

    @property
    def avg_cost_cents(self) -> float:
        if self.total_shares == 0:
            return 0.0
        return self.total_cost_cents / self.total_shares

    @property
    def realized_pnl_cents(self) -> int:
        return self.total_proceeds_cents - self._cost_of_exited_shares()

    @property
    def is_active(self) -> bool:
        return self.status in (PositionStatus.ACTIVE, PositionStatus.CAPITAL_RECOVERED)

    def _cost_of_exited_shares(self) -> int:
        """Cost basis of shares that have been sold."""
        exited_shares = self.total_shares - self.shares_remaining
        return int(exited_shares * self.avg_cost_cents)

    def current_value_cents(self, current_price_cents: int) -> int:
        """Current market value of remaining shares."""
        return self.shares_remaining * current_price_cents

    def current_pnl_cents(self, current_price_cents: int) -> int:
        """Unrealized + realized P&L."""
        remaining_cost = int(self.shares_remaining * self.avg_cost_cents)
        remaining_value = self.current_value_cents(current_price_cents)
        return (remaining_value - remaining_cost) + self.realized_pnl_cents

    def current_return_pct(self, current_price_cents: int) -> float:
        """Total return as a percentage of total cost."""
        if self.total_cost_cents == 0:
            return 0.0
        total_value = self.current_value_cents(current_price_cents) + self.total_proceeds_cents
        return (total_value - self.total_cost_cents) / self.total_cost_cents

    def price_gain_multiple(self, current_price_cents: int) -> float:
        """Current price as a multiple of average entry cost."""
        if self.avg_cost_cents == 0:
            return 0.0
        return current_price_cents / self.avg_cost_cents

    def add_entry(self, entry: EntryRecord):
        """Record a new entry into this position."""
        self.entries.append(entry)
        self.entry_count = len(self.entries)
        self.total_shares += entry.shares
        self.shares_remaining += entry.shares
        self.total_cost_cents += entry.cost_cents
        if entry.budget_source == "NUCLEAR_RESERVE":
            self.nuclear_budget_used_cents += entry.cost_cents
        else:
            self.game_budget_used_cents += entry.cost_cents
        self.updated_at = datetime.utcnow()

    def add_exit(self, exit_record: ExitRecord):
        """Record an exit (partial or full)."""
        self.exits.append(exit_record)
        self.shares_remaining -= exit_record.shares
        self.total_proceeds_cents += exit_record.proceeds_cents
        self.updated_at = datetime.utcnow()

        if self.shares_remaining <= 0:
            self.shares_remaining = 0
            self.closed_at = datetime.utcnow()

    def update_highest_price(self, current_price_cents: int):
        """Track the highest price seen (for trailing stop)."""
        if current_price_cents > self.highest_price_cents:
            self.highest_price_cents = current_price_cents
            self.updated_at = datetime.utcnow()


@dataclass
class EntrySignal:
    """Generated when a strategy identifies a potential trade."""
    signal_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: datetime = field(default_factory=datetime.utcnow)
    game_id: str = ""
    team: str = ""
    strategy: Strategy = Strategy.TIERED
    kalshi_ticker: str = ""
    contract_side: ContractSide = ContractSide.FAVORITE_YES
    entry_number: int = 1

    # Why we're entering
    kalshi_price_cents: int = 0
    fair_value: Optional[float] = None
    edge: Optional[float] = None
    deficit_vs_spread: float = 0.0
    price_drop_pct: Optional[float] = None
    pre_game_spread: float = 0.0

    # Context
    quarter: int = 0
    time_remaining_seconds: int = 0
    momentum_score: float = 0.0
    confidence: int = 50             # 0-100

    # Sizing
    suggested_shares: int = 0
    suggested_cost_cents: int = 0
    budget_source: str = "GAME_BUDGET"

    # Order book
    orderbook_depth: int = 0
    bid_ask_spread_cents: int = 0

    # Result
    action_taken: bool = False
    skip_reason: str = ""
    reason: str = ""


@dataclass
class TradeRecord:
    """Immutable record of a trade, saved to database."""
    trade_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: datetime = field(default_factory=datetime.utcnow)
    position_id: str = ""
    game_id: str = ""
    kalshi_ticker: str = ""
    team: str = ""
    strategy: Strategy = Strategy.TIERED
    action: TradeAction = TradeAction.BUY
    entry_number: Optional[int] = None
    price_cents: int = 0
    shares: int = 0
    total_cents: int = 0
    pnl_cents: Optional[int] = None
    reason: str = ""

    # Game state snapshot at time of trade
    game_quarter: int = 0
    game_time_remaining_seconds: int = 0
    game_score_home: int = 0
    game_score_away: int = 0
    deficit_vs_spread: float = 0.0
    fair_value: Optional[float] = None
    edge: Optional[float] = None
    price_drop_pct: Optional[float] = None
    orderbook_depth: int = 0
    game_mode: GameMode = GameMode.OFFENSIVE


@dataclass
class InjuryEvent:
    """Tracked when we detect a potential or confirmed injury."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: datetime = field(default_factory=datetime.utcnow)
    game_id: str = ""
    player_name: str = ""
    team: str = ""
    detection_method: str = ""       # "PBP_ABSENCE" or "OFFICIAL_REPORT"
    severity: InjurySeverity = InjurySeverity.POTENTIAL
    confirmed: bool = False
    action_taken: str = ""           # What we did in response
    position_id: Optional[str] = None  # If we had a position affected


@dataclass
class DailyPerformance:
    """End-of-day summary for one strategy."""
    date: str = ""
    strategy: Strategy = Strategy.TIERED
    starting_balance_cents: int = 0
    ending_balance_cents: int = 0
    pnl_cents: int = 0
    trades_count: int = 0
    wins: int = 0
    losses: int = 0
    best_trade_cents: int = 0
    worst_trade_cents: int = 0
    avg_win_cents: int = 0
    avg_loss_cents: int = 0
