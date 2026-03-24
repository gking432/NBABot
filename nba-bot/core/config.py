"""
All configuration and strategy parameters in one place.
Change thresholds here — not scattered across strategy files.
"""
import os
from dotenv import load_dotenv

load_dotenv()


# ─────────────────────────────────────────────
# API Configuration
# ─────────────────────────────────────────────

KALSHI_ENV = os.getenv("KALSHI_ENV", "demo")
KALSHI_BASE_URL = (
    "https://demo-api.kalshi.co/trade-api/v2"
    if KALSHI_ENV == "demo"
    else "https://api.elections.kalshi.com/trade-api/v2"
)
KALSHI_API_KEY_ID = os.getenv("KALSHI_API_KEY_ID", "")
KALSHI_PRIVATE_KEY_PATH = os.getenv("KALSHI_PRIVATE_KEY_PATH", "./kalshi-key.pem")

ODDS_API_KEY = os.getenv("ODDS_API_KEY", "")
ODDS_API_BASE_URL = "https://api.the-odds-api.com/v4"

BETSTACK_API_KEY = os.getenv("BETSTACK_API_KEY", "")

ESPN_BASE_URL = "http://site.api.espn.com/apis/site/v2/sports/basketball/nba"
NBA_CDN_BASE_URL = "https://cdn.nba.com/static/json/liveData"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# ─────────────────────────────────────────────
# Bot Settings
# ─────────────────────────────────────────────

PAPER_TRADING = os.getenv("PAPER_TRADING", "true").lower() == "true"
# Reset to $100 per strategy across 8 strategies = $800
INITIAL_BANKROLL_CENTS = int(os.getenv("INITIAL_BANKROLL_CENTS", "80000"))  # $800.00
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Main loop timing (seconds)
MAIN_LOOP_INTERVAL = 15          # How often the main loop runs
SNAPSHOT_INTERVAL = 30           # How often to log game snapshots to DB
ODDS_POLL_INTERVAL = 90          # BetStack: every 90s (rate limit: 1 req/60s, with buffer)
KALSHI_POLL_INTERVAL = 10        # Kalshi price refresh
KALSHI_REDISCOVER_INTERVAL = 300  # Re-discover NBA markets every 5 min (they may appear when games start)
ESPN_POLL_INTERVAL = 15          # ESPN score refresh
INJURY_CHECK_INTERVAL = 120      # Check for injuries every 2 minutes

# Game hours (ET) - only poll Odds API during this window
GAME_HOURS_START_ET = 19  # 7 PM ET
GAME_HOURS_END_ET = 1     # 1 AM ET (next day)

# Database
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "trading_bot.db")

# Dashboard
DASHBOARD_PORT = 8000
DASHBOARD_REFRESH_SECONDS = 10

# ─────────────────────────────────────────────
# Bankroll Allocation (% of total)
# ─────────────────────────────────────────────

# If true, override % allocations and assign a fixed bankroll per strategy.
USE_FIXED_STRATEGY_BANKROLLS = True
FIXED_STRATEGY_BANKROLL_CENTS = 10000  # $100 per strategy

CONSERVATIVE_BANKROLL_PCT = 0.30        # 30%
TIERED_BANKROLL_PCT = 0.30              # 30% (V2: entry-price-scaled exits)
TIERED_CLASSIC_BANKROLL_PCT = 0.30      # 30% (Classic: original 1.75x/3x/5x exits)
GARBAGE_TIME_BANKROLL_PCT = 0.10        # 10%

# ─────────────────────────────────────────────
# Strategy 1: CONSERVATIVE
# ─────────────────────────────────────────────

CONS_MIN_DEFICIT_VS_SPREAD = 12
CONS_MIN_SPREAD = 1.0            # Allow regime-aware Conservative filtering by edge
CONS_MIN_EDGE_PCT = 0.08           # 8% minimum edge (fair_value - kalshi_price/100)
CONS_CLOSE_SPREAD_MAX = 3.5
CONS_CLOSE_MIN_EDGE_PCT = 0.13     # Require higher edge in close-spread games
CONS_MID_MIN_EDGE_PCT = 0.10       # Moderate edge for mid spread games
CONS_MAX_ENTRY_PRICE_CENTS = 35    # Won't buy above 35¢
CONS_MIN_BOOK_DEPTH = 100          # Minimum contracts at the ask
CONS_MAX_ENTRY_QUARTER = 2         # No entries after Q2

# Conservative position sizing (% of conservative bankroll)
CONS_SIZE_EDGE_8_10 = 0.08         # 8% when edge 8-10%
CONS_SIZE_EDGE_10_12 = 0.12        # 12% when edge 10-12%
CONS_SIZE_EDGE_12_PLUS = 0.16      # 16% when edge 12%+

# Conservative exits
CONS_TP1_PCT = 0.30                # Take profit 1: sell 50% at +30%
CONS_TP1_SELL_PCT = 0.50           # Sell 50% of shares
CONS_TP2_PCT = 0.60                # Take profit 2: sell remaining at +60%
CONS_TP2_SELL_PCT = 1.00           # Sell all remaining
CONS_STOP_LOSS_PCT = -0.30         # Stop loss at -30%
CONS_STOP_LOSS_MIN_HOLD_MINUTES = 12  # Must hold 12+ min before stop fires
CONS_THESIS_INVALID_DEFICIT = 25   # Deficit > 25 invalidates thesis
CONS_THESIS_INVALID_MIN_QUARTER = 3
CONS_THESIS_INVALID_MAX_TIME_SEC = 480  # < 8 minutes remaining

# Conservative limits
CONS_MAX_CONCURRENT_POSITIONS = 2

# ─────────────────────────────────────────────
# Strategy 2: TIERED
# ─────────────────────────────────────────────

TIER_MIN_SPREAD = 1                # Pre-game spread at least 1
TIER_MAX_SPREAD = 7                # Pre-game spread at most 7
TIER_CLOSE_SPREAD_MAX = 3.5        # <=3.5 treated as close-spread scalp regime
TIER_MIN_DEFICIT_VS_SPREAD = 10
TIER_MIN_PRICE_DROP_PCT = 0.00     # No minimum drop for Entry 1
TIER_MAX_ENTRY_PRICE_CENTS = 35    # Won't buy above 35¢
TIER_MIN_BOOK_DEPTH = 50
TIER_MAX_ENTRY_QUARTER = 2         # Entries 1-4 only in Q1/Q2

# Tiered multi-entry rules
TIER_ENTRY2_MIN_ADDITIONAL_DROP_PCT = 0.25   # Price must drop 25% more from Entry 1
TIER_ENTRY2_MIN_ADDITIONAL_DEFICIT = 0       # No extra deficit growth required for Entry 2
TIER_ENTRY2_MIN_TIME_LEFT_Q2_SEC = 360       # At least 6 min left in Q2 for Entry 2
TIER_ENTRY34_MIN_ADDITIONAL_DROP_PCT = 0.25  # Same for Entry 3/4
TIER_ENTRY4_MIN_TIME_LEFT_Q2_SEC = 480       # At least 8 min left in Q2 for Entry 4
TIER_ENTRY3_MIN_SPREAD = 6.0                 # Entry 3/4 only in stronger spread regime

# Q3 Entry-2 override (aggressive early-3Q averaging)
TIER_ENTRY2_Q3_WINDOW_SEC = 360              # First 6 minutes of Q3
TIER_ENTRY2_Q3_MIN_DROP_PCT = 0.15           # 15% drop vs Entry 1
TIER_ENTRY2_Q3_DEFICIT_GROWTH = 0            # No extra deficit growth required
TIER_ENTRY2_Q3_MIN_BOOK_DEPTH = 50

# Tiered position sizing (% of tiered bankroll)
TIER_GAME_BUDGET_PCT = 0.24        # 24% game budget, split 50/50 for Entry 1 & 2
TIER_NUCLEAR_BUDGET_PCT = 0.24     # 24% nuclear reserve for Entry 3 & 4
TIER_MAX_PER_GAME_PCT = 0.48       # 48% max total per game

# ─── Quick Scalp Exit System ───
TIER_SCALP_PROFIT_PCT = 0.175      # Sell 50% at +17.5%
TIER_SCALP_PARTIAL_SELL_PCT = 0.50
TIER_SCALP_PRICE_TARGET_CENTS = 40
TIER_SCALP_HIGH_AVG_TARGET_CENTS = 48
TIER_SCALP_AVG_COST_THRESHOLD = 30
TIER_SCALP_RECOVERY_ENTRIES = 3
TIER_SCALP_RECOVERY_STOP_LOSS_PCT = 0.60  # Wider stop for 3+ entry recovery positions

# Close-spread scalp geometry (spread <= 3.5)
TIER_CLOSE_MAX_ENTRIES = 2
TIER_CLOSE_TP1_ADD_CENTS = 6
TIER_CLOSE_TP2_ADD_CENTS = 10
TIER_CLOSE_TP2_CEILING_CENTS = 42
TIER_CLOSE_STOP_LOSS_PCT = 0.25
TIER_CLOSE_TIME_EXIT_Q3_SEC = 300

# Universal per-position tail cap
TIER_MAX_POSITION_LOSS_PCT = 0.55
TIER_TIME_EXIT_Q4_SEC = 300

# Tiered limits
TIER_MAX_CONCURRENT_POSITIONS = 3

# ─────────────────────────────────────────────
# Strategy 2b: TIERED CLASSIC (original exit logic)
# Entry rules are shared with Tiered V2 above.
# ─────────────────────────────────────────────

TIER_CLASSIC_MAX_ENTRY_PRICE_CENTS = 40    # Original 40¢ cap

# Classic exits (reachable staged multipliers)
TIER_CLASSIC_CAPITAL_RECOVERY_MULT = 1.5
TIER_CLASSIC_CAPITAL_RECOVERY_SELL_PCT = 0.50
TIER_CLASSIC_HOUSE_MONEY_1_MULT = 2.0
TIER_CLASSIC_HOUSE_MONEY_1_SELL_PCT = 0.25
TIER_CLASSIC_HOUSE_MONEY_2_MULT = 2.2
TIER_CLASSIC_HOUSE_MONEY_2_SELL_PCT = 0.25
TIER_CLASSIC_LATE_GAME_PRICE_CENTS = 80
TIER_CLASSIC_LATE_GAME_SELL_PCT = 0.60
TIER_CLASSIC_TRAILING_STOP_PCT = 0.50

# Classic stop loss
TIER_CLASSIC_DEFENSIVE_HARD_FLOOR_PCT = 0.15
TIER_CLASSIC_UNIVERSAL_STOP_PCT = 0.60    # -60% unrealized loss = sell all (Q3+ only)
TIER_CLASSIC_RECOVERY_ENTRIES = 3         # 3+ entries = capital recovery (sell at breakeven)
TIER_CLASSIC_RECOVERY_STOP_LOSS_PCT = 0.60
TIER_CLASSIC_MAX_POSITION_LOSS_PCT = 0.55

# Classic limits
TIER_CLASSIC_MAX_CONCURRENT_POSITIONS = 3

# ─────────────────────────────────────────────
# Strategy 3: BOUNCEBACK (Q3 Halftime-Dip Specialist)
# Buy the favorite's contract at the start of Q3 when
# they're trailing by a moderate margin. Exploits halftime
# pessimism selling and Q3 comeback patterns.
# ─────────────────────────────────────────────

# Entry conditions
GT_MIN_SPREAD = 5                   # Pre-game spread at least 5 (strong favorite)
GT_ENTRY_WINDOW_Q3_SEC = 360        # First 6 min of Q3 (time_remaining >= 360)
GT_MIN_TRAILING_POINTS = 6          # Favorite must be losing by at least 6
GT_MAX_TRAILING_POINTS = 18         # But not more than 18 (blowout = low comeback rate)
GT_MIN_DEFICIT_VS_SPREAD = 8        # Deficit vs spread must be >= 8
GT_MIN_PRICE_CENTS = 15             # Kalshi yes_ask must be >= 15¢
GT_MAX_PRICE_CENTS = 42             # Don't buy above 42¢ (need asymmetric payoff)
GT_MIN_PRICE_DROP_PCT = 0.15        # Price must have dropped 15%+ from tipoff
GT_MIN_BOOK_DEPTH = 25              # Minimum contracts on the book
GT_MIN_EDGE_PCT = 0.06              # 6% edge vs fair value (if available)

# Sizing
GT_BUDGET_PCT = 0.14                # 14% of bankroll per game
GT_ENTRY1_BUDGET_SPLIT = 0.70       # 70% of game budget for Entry 1, 30% for Entry 2

# Entry 2 (averaging down)
GT_ENTRY2_MIN_DROP_PCT = 0.20       # Price must drop 20% from Entry 1
GT_ENTRY2_MIN_TIME_Q3_SEC = 180     # Must have >= 3 min left in Q3
GT_ENTRY2_MAX_DEFICIT = 25          # Deficit can't have grown past 25

# Exits
GT_TP1_PCT = 0.30                   # Take profit 1: +30% → sell 50%
GT_TP1_SELL_PCT = 0.50              # Sell 50% of shares
GT_TP2_PRICE_CENTS = 50             # Take profit 2: price >= 50¢ → sell remaining
GT_STOP_LOSS_PCT = 0.35             # Stop loss at -35% (after hold period)
GT_STOP_MIN_HOLD_SEC = 360          # Must hold 6 min before stop fires
GT_THESIS_INVALID_DEFICIT = 30      # Deficit > 30 = thesis dead, sell all
GT_TIME_EXIT_Q4_SEC = 300           # Q4 with < 5 min left → sell at market

# Limits
GT_MAX_CONCURRENT_POSITIONS = 3

# ─────────────────────────────────────────────
# Strategy 4: PULSE (Aggressive Momentum Scalp)
# ─────────────────────────────────────────────

PULSE_MIN_SPREAD = 1
PULSE_MAX_SPREAD = 12
PULSE_MIN_DEFICIT_VS_SPREAD = 6
PULSE_MIN_PRICE_DROP_PCT = 0.10
PULSE_MAX_ENTRY_PRICE_CENTS = 60
PULSE_MIN_BOOK_DEPTH = 20
PULSE_MAX_ENTRY_QUARTER = 3

PULSE_BUDGET_PCT = 0.12           # 12% of bankroll per position
PULSE_TP1_PCT = 0.12              # +12% take profit
PULSE_TP1_SELL_PCT = 0.60
PULSE_TP2_PCT = 0.25              # +25% take profit
PULSE_TP2_SELL_PCT = 1.00
PULSE_STOP_LOSS_PCT = -0.12       # -12% stop
PULSE_STOP_MIN_HOLD_MINUTES = 4

PULSE_MAX_CONCURRENT_POSITIONS = 4

# ─────────────────────────────────────────────
# Time-Based Game Modes
# ─────────────────────────────────────────────

# Neutral mode: first N seconds of Q3 game time
NEUTRAL_MODE_Q3_WINDOW_SEC = 360   # First 6 minutes of Q3

# Transition from neutral to defensive
NEUTRAL_TO_DEFENSIVE_DEFICIT_GROWING_MIN_SEC = 240  # If deficit growing for 4+ min in Q3

# ─────────────────────────────────────────────
# Injury Detection
# ─────────────────────────────────────────────

INJURY_ABSENCE_THRESHOLD_SEC = 300  # 5 minutes of game time without appearing in PBP

# ─────────────────────────────────────────────
# Risk Management (Global)
# ─────────────────────────────────────────────

DAILY_LOSS_LIMIT_PCT = 0.30         # 30% of strategy bankroll → pause that game only
WEEKLY_LOSS_LIMIT_PCT = 0.25        # 25% → pause and review
GLOBAL_HARD_FLOOR_PCT = 0.60        # Total bankroll < 60% of start → everything pauses
MAX_LIQUIDITY_CONSUMPTION_PCT = 0.30  # Don't consume > 30% of visible book depth
NO_TRADE_FINAL_MINUTES_SEC = 120     # No new trades in final 2 minutes of game
MAX_SLIPPAGE_ALERT_CENTS = 3         # Alert if avg slippage > 3¢
