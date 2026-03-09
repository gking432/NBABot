# NBA Kalshi Trading Bot — Final Build Guide for Cursor

> **This document is the complete specification for building an NBA prediction market trading bot. It contains every API endpoint, every strategy rule, every data model, every dashboard view, and every edge case. Build Phase 1 first, then Phase 2, then Phase 3. Do not skip ahead.**

---

## ⚠️ 2026 Strategy Update (Canonical Behavior)

To prevent drift/confusion, the current bot behavior now follows the **regime-aware** strategy model implemented in code:

- **Tiered V2 is regime-aware**:
  - `opening_spread <= 3.5` → close-spread scalp mode (max 2 entries, avg-relative TP/SL/time-stop)
  - `opening_spread > 3.5` → recovery mode with stricter Entry 3+ gating and explicit tail-loss caps
- **Tiered Classic has reachable exits** (`1.5x / 2.0x / 2.2x`) and explicit recovery/tail stops.
- **Conservative uses spread-aware edge thresholds** (higher required edge in close spreads).
- **Heavy Favorite enforces universal tail-loss cap** and Entry 3+ spread gating.
- **Weekly governance scorecard** is part of the core workflow via `nba-bot/tools/weekly_scorecard.py` with outputs:
  - `nba-bot/docs/weekly_scorecard.md`
  - `nba-bot/docs/weekly_scorecard.json`

### Canonical source of truth
For active strategy rules and paper-trading governance protocol, use:
- `nba-bot/docs/STRATEGY_PHASES_IMPLEMENTATION.md`
- `nba-bot/core/config.py`
- `nba-bot/strategies/*.py`

This document remains useful as full-system background, but if any section conflicts with the files above, treat the files above as authoritative.

---

## TABLE OF CONTENTS

1. Architecture Overview
2. API Specifications (Every Endpoint)
3. Data Models
4. Strategy 1: Conservative
5. Strategy 2: Tiered
6. Strategy 3: Heavy Favorite Collapse
7. Multi-Entry System
8. Time-Based Game Modes
9. Exit Logic (All Strategies)
10. Injury Detection & Response
11. Risk Management
12. Dashboard Specification (6 Tabs)
13. Database Schema
14. File Structure
15. Phase 1 (Week 1): Foundation + Paper Trading
16. Phase 2 (Week 2): Production Kalshi + Fair Value Model
17. Phase 3 (Week 3): Dashboard + Advanced Signals + Optimization

---

## 1. ARCHITECTURE OVERVIEW

```
┌──────────────────────────────────────────────────────────────┐
│                     MAIN BOT LOOP (every 15 seconds)         │
│                                                              │
│  DATA LAYER:                                                 │
│  ┌────────────┐  ┌─────────────┐  ┌────────────────────┐   │
│  │ ESPN/NBA   │  │ The Odds    │  │ Kalshi API         │   │
│  │ (Scores)   │  │ API (Vegas) │  │ (Market Prices)    │   │
│  │ Free, 15s  │  │ Free, 5min  │  │ Free, 10-15s       │   │
│  └─────┬──────┘  └──────┬──────┘  └─────────┬──────────┘   │
│        │                │                    │               │
│        ▼                ▼                    ▼               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              DATA AGGREGATOR                          │   │
│  │  Merges all sources into LiveGameState per game       │   │
│  │  Calculates: deficit, fair_value, edge, price_drop    │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  STRATEGY LAYER:        ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Conservative │ Tiered │ Heavy Favorite Collapse      │   │
│  │  (edge-based) │(price  │ (wide spread + big deficit)  │   │
│  │               │ drop)  │                               │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  EXECUTION LAYER:       ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Paper Trading Engine (Week 1-3)                      │   │
│  │  → Uses real Kalshi prices, simulates order fills     │   │
│  │  Live Trading Engine (Week 4+)                        │   │
│  │  → Sends real orders to Kalshi                        │   │
│  └──────────────────────┬───────────────────────────────┘   │
│                         │                                    │
│  STORAGE + UI:          ▼                                    │
│  ┌─────────────────┐  ┌────────────────────────────────┐   │
│  │ SQLite Database  │  │ FastAPI Dashboard (6 tabs)     │   │
│  │ Every snapshot,  │  │ localhost:8000                  │   │
│  │ signal, trade    │  │ Real-time updates every 10s    │   │
│  └─────────────────┘  └────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

**Key design decisions:**
- Paper trading uses REAL Kalshi market prices. Only order execution is simulated.
- Three independent strategies, each with their own bankroll allocation.
- SQLite for all persistence. Every game state, every signal, every trade logged.
- FastAPI dashboard runs in a background thread. No separate server process.

---

## 2. API SPECIFICATIONS

### 2A. Kalshi API v2

**Base URLs:**
- Demo: `https://demo-api.kalshi.co/trade-api/v2`
- Production: `https://trading-api.kalshi.com/trade-api/v2`

**Authentication: RSA Key Signature (NOT email/password)**

The old bot used email/password login. That's Kalshi v1 and is broken. Kalshi v2 requires:

1. Generate an API key pair in the Kalshi dashboard (Settings → API Keys)
2. Download the private key file (.key or .pem)
3. For every request, sign: `timestamp_ms + HTTP_METHOD + path` (path without query params)
4. Send three headers: `KALSHI-ACCESS-KEY`, `KALSHI-ACCESS-SIGNATURE`, `KALSHI-ACCESS-TIMESTAMP`

```python
# Authentication implementation:
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import base64, time

def load_private_key(file_path: str):
    with open(file_path, "rb") as f:
        return serialization.load_pem_private_key(
            f.read(), password=None, backend=default_backend()
        )

def get_auth_headers(api_key_id: str, private_key, method: str, path: str) -> dict:
    timestamp_ms = str(int(time.time() * 1000))
    # IMPORTANT: Strip query params from path before signing
    path_for_signing = path.split('?')[0]
    message = timestamp_ms + method.upper() + path_for_signing
    
    signature = private_key.sign(
        message.encode('utf-8'),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.MAX_LENGTH
        ),
        hashes.SHA256()
    )
    
    return {
        'KALSHI-ACCESS-KEY': api_key_id,
        'KALSHI-ACCESS-SIGNATURE': base64.b64encode(signature).decode('utf-8'),
        'KALSHI-ACCESS-TIMESTAMP': timestamp_ms,
        'Content-Type': 'application/json'
    }
```

**Endpoints we use:**

```
# Discover NBA markets
GET /events?series_ticker=NBA&status=open
→ Returns events, each containing markets
→ Use event_ticker to find specific games

# Get market details (prices, volume)
GET /markets/{ticker}
→ Returns: yes_bid, yes_ask, no_bid, no_ask, last_price, volume_24h,
   open_interest, status
→ ALL PRICES IN CENTS (1-99)

# Get order book depth
GET /markets/{ticker}/orderbook
→ Returns: yes (array of [price_cents, quantity]), no (array)
→ Check depth before entering any trade

# Get trade history (for finding opening price)
GET /markets/trades?ticker={ticker}&limit=100
→ Returns: [{yes_price, no_price, count, created_time, taker_side}]
→ First trade after market opens = opening price
→ First trade after game tips off = tipoff price

# Place order (live trading only, Week 4+)
POST /portfolio/orders
→ Body: {ticker, action, side, count, type: "limit", yes_price or no_price}
→ Always use limit orders, never market orders

# Check balance and positions
GET /portfolio/balance → {balance: <cents>}
GET /portfolio/positions → [{ticker, market_exposure, ...}]
```

**Rate limits:** 10 reads/sec, 5 writes/sec. Implement exponential backoff on HTTP 429.

**Kalshi NBA market ticker format:**
Tickers vary. Do NOT hardcode format. Always discover via GET /events?series_ticker=NBA.
Then get markets within each event. Filter for moneyline/winner markets.

---

### 2B. ESPN Scoreboard API (Free, No Key)

```
GET http://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard
```

No auth. Poll every 15 seconds. Returns all games for today.

**Key fields:**
```json
{
  "events": [{
    "id": "401584766",
    "status": {
      "type": {"state": "in"},       // "pre", "in", "post"
      "period": 2,                    // quarter (5+ = overtime)
      "displayClock": "6:42"          // time remaining in quarter
    },
    "competitions": [{
      "competitors": [
        {
          "homeAway": "home",
          "team": {"displayName": "Los Angeles Lakers", "abbreviation": "LAL"},
          "score": "52"
        },
        {
          "homeAway": "away", 
          "team": {"displayName": "Boston Celtics", "abbreviation": "BOS"},
          "score": "48"
        }
      ],
      "odds": [{
        "spread": -5.5,       // PRE-GAME ONLY. Often missing during live play.
        "overUnder": 224.5
      }]
    }]
  }]
}
```

**CRITICAL:** ESPN odds[].spread is PRE-GAME ONLY and often stale/missing during live play. Use it only for the opening spread. Get live odds from The Odds API.

---

### 2C. NBA CDN API (Free, No Key, Backup + Play-by-Play)

```
# Live scoreboard (backup for ESPN)
GET https://cdn.nba.com/static/json/liveData/scoreboard/todaysScoreboard_00.json

# Box score for specific game
GET https://cdn.nba.com/static/json/liveData/boxscore/boxscore_{gameId}.json

# Play-by-play (for momentum detection + injury absence detection)
GET https://cdn.nba.com/static/json/liveData/playbyplay/playbyplay_{gameId}.json
```

No auth. Game IDs are in format "0022400XXX" (different from ESPN IDs — map via team names + date).

**We use play-by-play for:**
- Momentum detection: did a team outscore opponent by 8+ in last 3-4 minutes?
- Injury absence detection: has a star player disappeared from events for 5+ minutes of game time?
- Scoring run detection: 8+ unanswered points = signal

---

### 2D. The Odds API (Free: 500 requests/month)

```
GET https://api.the-odds-api.com/v4/sports/basketball_nba/odds
  ?apiKey=YOUR_API_KEY
  &regions=us
  &markets=h2h,spreads
  &oddsFormat=american
```

Sign up at https://the-odds-api.com. API key goes in query string.

**Budget strategy for 500 requests/month:**
- Each request returns ALL live + upcoming NBA games
- Poll every 5 minutes during game hours only (7 PM - 1 AM ET)
- ~72 requests per game night × 7 nights = ~504/month (tight but workable)
- Track remaining quota via response header: `x-requests-remaining`

**What we extract per game:**
```python
# From each bookmaker's moneyline:
def american_to_probability(odds: int) -> float:
    if odds < 0:
        return abs(odds) / (abs(odds) + 100)
    return 100 / (odds + 100)

# Fair value calculation:
# 1. Convert each bookmaker's moneyline to implied probability
# 2. For each bookmaker, remove vig:
#    fair_home = prob_home / (prob_home + prob_away)
# 3. Take median across all bookmakers (robust to outliers)
# 4. This median is our "fair value" — what the team should be priced at
```

**Response structure:**
```json
{
  "id": "abc123",
  "home_team": "Los Angeles Lakers",
  "away_team": "Boston Celtics",
  "commence_time": "2025-02-15T01:00:00Z",
  "bookmakers": [{
    "key": "draftkings",
    "markets": [{
      "key": "h2h",
      "outcomes": [
        {"name": "Los Angeles Lakers", "price": -220},
        {"name": "Boston Celtics", "price": +180}
      ]
    }, {
      "key": "spreads",
      "outcomes": [
        {"name": "Los Angeles Lakers", "price": -110, "point": -5.5},
        {"name": "Boston Celtics", "price": -110, "point": 5.5}
      ]
    }]
  }]
}
```

---

### 2E. Injury Detection Sources (Free)

**Source 1: `nbainjuries` Python package**
```
pip install nbainjuries
```
Scrapes the official NBA injury report from NBA.com. Reports are updated during games when a player's status changes (e.g., "out for remainder"). Delay: 10-15 minutes from actual injury to report update. This is our CONFIRMED source.

**Source 2: NBA play-by-play absence detection**
Monitor play-by-play feed. If a top-3 player by minutes hasn't appeared in any event for 5+ minutes of game time, flag as potential injury. This is our EARLY WARNING source (3-5 minute detection).

**Source 3 (Future, not v1): Twitter/X API**
NBA injury news breaks on Twitter within 60 seconds via reporters. Real-time keyword monitoring on specific accounts would be near-instant detection. This is a paid API and a v2/v3 feature.

---

### 2F. BallDontLie API (Free tier, historical data)

```
GET https://api.balldontlie.io/v1/games?dates[]=2025-02-15
Headers: Authorization: YOUR_API_KEY
```

Free tier: 30 requests/minute. Useful for historical game data and building regression models. Not needed for live trading — ESPN and NBA CDN cover live data.

---

## 3. DATA MODELS

### LiveGameState (central data object — everything we know about a game)

```python
@dataclass
class LiveGameState:
    # Identifiers
    game_id_espn: str
    game_id_nba: Optional[str]
    kalshi_event_ticker: Optional[str]
    kalshi_market_ticker: Optional[str]   # the actual tradeable market
    
    # Teams (canonical names, normalized across all APIs)
    home_team: str
    away_team: str
    favorite: str
    underdog: str
    
    # Live Score
    home_score: int
    away_score: int
    quarter: int                     # 1-4, 5+ = overtime
    time_remaining_seconds: int      # seconds remaining in current quarter
    game_status: str                 # "pre", "live", "halftime", "final"
    
    # Spreads & Odds
    opening_spread: float            # from ESPN at tipoff (e.g., -5.5)
    current_spread: float            # from The Odds API (live consensus)
    fair_value_home: float           # vig-removed implied prob (0-1)
    fair_value_away: float
    odds_last_updated: datetime
    
    # Kalshi Market Data (ALL IN CENTS)
    kalshi_yes_bid: int              # best bid in cents
    kalshi_yes_ask: int              # best ask in cents (this is what we pay to buy)
    kalshi_last_price: int
    kalshi_volume: int
    kalshi_open_interest: int
    kalshi_opening_price: int        # first trade price at market open
    kalshi_tipoff_price: int         # price when game tipped off
    kalshi_book_depth: int           # total qty available in top 5 ask levels
    kalshi_bid_ask_spread: int       # yes_ask - yes_bid
    
    # Derived Signals
    deficit_vs_spread: float         # how much worse than spread (always positive)
    score_differential: int          # from our team's perspective (negative = losing)
    edge_conservative: float         # fair_value - (kalshi_yes_ask / 100)
    price_drop_from_tipoff: float    # (tipoff_price - current_ask) / tipoff_price
    momentum_score: float            # -1 to 1 (from play-by-play analysis)
    
    # Timestamps
    last_score_update: datetime
    last_kalshi_update: datetime
    last_odds_update: datetime
```

### Position

```python
@dataclass
class Position:
    position_id: str
    game_id: str
    kalshi_ticker: str
    team: str
    strategy: str                    # "CONSERVATIVE", "TIERED", "HEAVY_FAVORITE"
    
    # Entry tracking (supports multiple entries)
    entries: List[dict]              # [{time, quarter, price_cents, shares, cost_cents}]
    total_shares: int
    total_cost_cents: int
    avg_cost_cents: float            # weighted average entry price
    entry_count: int                 # how many times we've entered (1, 2, 3, or 4)
    
    # Budget tracking
    game_budget_used_cents: int      # from normal allocation
    nuclear_budget_used_cents: int   # from reserve allocation
    
    # State
    shares_remaining: int
    status: str                      # "ACTIVE", "CAPITAL_RECOVERED", "CLOSED_WIN",
                                     # "CLOSED_LOSS", "CLOSED_SETTLED_WIN", 
                                     # "CLOSED_SETTLED_LOSS"
    capital_recovered: bool
    capital_recovered_amount_cents: int
    highest_price_cents: int         # for trailing stop
    current_mode: str                # "OFFENSIVE", "NEUTRAL", "DEFENSIVE"
    
    # Exit tracking
    exits: List[dict]                # [{time, price_cents, shares, proceeds_cents, reason}]
    realized_pnl_cents: int
```

### EntrySignal

```python
@dataclass
class EntrySignal:
    game_state: LiveGameState
    team: str
    strategy: str
    entry_number: int                # 1, 2, 3, or 4 (which entry is this)
    
    # Why we're entering
    kalshi_price_cents: int          # the ask price we'd pay
    fair_value: Optional[float]      # conservative only
    edge: Optional[float]            # conservative only
    deficit_vs_spread: float
    price_drop_pct: Optional[float]  # tiered and heavy favorite
    pre_game_spread: float           # for heavy favorite sizing
    
    # Context
    quarter: int
    time_remaining_seconds: int
    confidence: int                  # 0-100
    reason: str                      # human-readable explanation
    
    # Sizing
    suggested_shares: int
    suggested_cost_cents: int
    budget_source: str               # "GAME_BUDGET" or "NUCLEAR_RESERVE"
    
    # Order book check
    orderbook_depth: int
    bid_ask_spread_cents: int
```

### TradeRecord (immutable, saved to database)

```python
@dataclass
class TradeRecord:
    trade_id: str
    timestamp: datetime
    game_id: str
    kalshi_ticker: str
    team: str
    strategy: str
    action: str                      # "BUY", "SELL_PARTIAL", "SELL_ALL", 
                                     # "SETTLED_WIN", "SETTLED_LOSS"
    entry_number: Optional[int]      # which entry (1-4) for buys
    price_cents: int
    shares: int
    total_cents: int
    pnl_cents: Optional[int]
    reason: str
    
    # Snapshot of game state at time of trade
    game_quarter: int
    game_time_remaining_seconds: int
    game_score_home: int
    game_score_away: int
    deficit_vs_spread: float
    fair_value: Optional[float]
    edge: Optional[float]
    price_drop_pct: Optional[float]
    orderbook_depth: int
    game_mode: str                   # OFFENSIVE, NEUTRAL, DEFENSIVE
```

---

## 4. STRATEGY 1: CONSERVATIVE

**Philosophy:** Only enter when we can mathematically prove Kalshi is mispriced relative to Vegas consensus.

**Bankroll allocation:** 35% of total bankroll.

**Entry checklist (ALL must be true):**
1. Game is live (game_status == "live")
2. Quarter is 1 or 2
3. Deficit vs spread ≥ 12 points
4. Edge ≥ 8% (fair_value minus kalshi_yes_ask/100)
5. Kalshi ask price ≤ 35¢
6. Order book depth ≥ 100 contracts at the ask
7. No existing conservative position in this game

**Single entry only.** No averaging down. One precise entry, defined exits.

**Position sizing:**
- Edge 8-10%: 4% of conservative bankroll
- Edge 10-12%: 6% of conservative bankroll
- Edge 12%+: 8% of conservative bankroll

**Exits:**
- Take profit 1: up 30% → sell 50% of shares
- Take profit 2: up 60% → sell remaining 50% of shares. Trade complete.
- Stop loss: down 30% AND held for 12+ minutes AND deficit still growing → sell all
- Thesis invalidation: deficit exceeds 25 AND quarter ≥ 3 AND time remaining < 8 min → sell all
- Game ends: market settles at $1.00 (win) or $0.00 (loss). Record result.

**No house money mode.** No re-entry after stop loss. Clean and mechanical.

---

## 5. STRATEGY 2: TIERED

**Philosophy:** Close-spread games where a team falls behind early. Multi-entry averaging down. House money exits on winners. Time-based defensive management on losers.

**Bankroll allocation:** 40% of total bankroll. Split into game budget (50%) and nuclear reserve (50%).

**Pre-game spread requirement:** 1-7 points.

**Entry 1 checklist (ALL must be true):**
1. Game is live
2. Quarter is 1 or 2
3. Pre-game spread is 1-7 points
4. Deficit vs spread ≥ 10 points
5. Kalshi price dropped ≥ 25% from tipoff price
6. Kalshi ask ≤ 40¢
7. Order book depth ≥ 50 contracts
8. No existing tiered position in this game

**Entry 2 — averaging down (same game):**
1. Entry 1 already placed
2. Still Q1 or early Q2 (at least 6 minutes left in Q2)
3. Price dropped ≥ 25% further from Entry 1 price
4. Deficit grew by ≥ 8 points since Entry 1
5. No in-game injury to key players on our team
6. Game budget not yet fully used

**Entry 3 — nuclear reserve (separate budget):**
1. Entry 1 and 2 already placed
2. Still Q1 or early Q2
3. Price dropped ≥ 25% further from Entry 2 price
4. No in-game injuries
5. Comes from nuclear reserve budget, NOT game budget

**Entry 4 — second nuclear (if price keeps dropping):**
1. Entry 3 already placed
2. Still Q1 or very early Q2 (at least 8 min left in Q2)
3. Price dropped further
4. No injuries
5. Remaining nuclear reserve budget

**Position sizing:**
- Game budget per game: 12% of tiered bankroll, split 50/50 for Entry 1 and Entry 2
- Nuclear reserve per game: up to another 12% of tiered bankroll, for Entry 3 and 4
- Maximum total per game: 24% of tiered bankroll across all entries

---

## 6. STRATEGY 3: HEAVY FAVORITE COLLAPSE

**Philosophy:** When a big Vegas favorite gets blown out early, buy at panic prices. The talent gap is real and there's a full game left for it to show.

**Bankroll allocation:** 25% of total bankroll. Split into game budget (50%) and nuclear reserve (50%).

**Pre-game spread requirement:** 8+ points (this is a BIG favorite).

**Entry 1 checklist (ALL must be true):**
1. Game is live
2. Quarter is 1 or early Q2 (at least 8 minutes left in Q2)
3. Pre-game spread ≥ 8 points
4. Deficit vs spread ≥ 15 points
5. Kalshi ask ≤ 30¢
6. No in-game injuries to key players on the favorite
7. Order book depth ≥ 50 contracts
8. No existing heavy favorite position in this game

**Entry 2, 3, 4:** Same multi-entry rules as Tiered strategy.

**Position sizing — spread-scaled confidence multiplier:**
- Base game budget: 12% of heavy favorite bankroll
- Spread 8-10: multiply by 1.0x (standard)
- Spread 10-12: multiply by 1.25x
- Spread 12+: multiply by 1.5x
- So a -13 favorite collapse might get up to 18% as game budget
- Plus nuclear reserve: up to another 18%
- Maximum total per game: up to 36% of heavy favorite bankroll (rare, extreme case)

**The wider the pre-game spread, the more confident we are.** Vegas doesn't set a 13-point spread lightly. That talent gap is real. At 5¢-15¢ on Kalshi in Q1, the risk/reward is heavily in our favor.

---

## 7. MULTI-ENTRY SYSTEM (applies to Tiered and Heavy Favorite)

The multi-entry system uses a **per-game budget** plus a **nuclear reserve.**

**Per-game budget:** The initial allocation for entries 1 and 2. Split 50/50.

**Nuclear reserve:** A separate pool of capital for entries 3 and 4. This is NOT part of the original game budget. It represents additional conviction when the setup gets even better (price drops further while still early in the game).

**Entry spacing rules:**
- Each subsequent entry requires the price to have dropped at least 25% further from the previous entry price
- Each subsequent entry must still be in Q1 or early Q2
- No new entries after halftime, ever (for averaging down — the time advantage is gone)
- Total entries per game capped at 4

**Average cost basis tracking:**
When averaging down, track the weighted average cost:
```
avg_cost = total_cents_invested / total_shares
```
This is what determines your breakeven point. With multiple entries at declining prices, the average cost drops significantly, making a recovery scenario much more achievable.

---

## 8. TIME-BASED GAME MODES

Every position cycles through three modes based on game time and position status. The mode determines what actions are allowed.

### OFFENSIVE MODE (Q1 and Q2)

**When:** Game is in Q1 or Q2 and position is active.

**Allowed actions:**
- All new entries (1 through 4)
- Hold all existing shares
- Take profit exits if triggered (house money system)

**Stop losses:** Extremely wide. The ONLY exit trigger in offensive mode is a confirmed in-game injury to a key player on our team (see Section 10 for response rules).

**Philosophy:** We entered early for a reason. Give the trade room to breathe. The price will likely get worse before it gets better. That's expected and okay.

### NEUTRAL MODE (first 6 minutes of Q3)

**When:** Q3 has started, fewer than 6 minutes of Q3 game time have elapsed.

**Allowed actions:**
- NO new entries
- Hold all existing shares
- Take profit exits if triggered
- Monitor deficit trajectory closely

**Transition rules:**
- If deficit is SHRINKING after 4-5 minutes of Q3 → stay in neutral, potentially shift back toward offensive mindset (still no new entries, but wide stops)
- If deficit is SAME or GROWING after 4-5 minutes of Q3 → transition to DEFENSIVE mode

**Philosophy:** This is the halftime adjustment window. Coaches make changes. Rotations shift. Give it a few minutes to see if the adjustment is working.

### DEFENSIVE MODE (late Q3 and Q4, when position is underwater)

**When:** Position is underwater AND (late Q3 or Q4). Also triggered by injury to a star on multi-star team at any point in the game.

**Allowed actions:**
- NO new entries
- Sell into any strength (any price uptick from a scoring run)
- Accept the loss gracefully — goal is damage control, not recovery

**How "sell into strength" works:**
NBA games almost always have mini scoring runs, even in blowouts. A 6-8 point run by the losing team will bump the Kalshi price temporarily (maybe 4¢ → 7¢). That bump is the exit window. Set a "defensive exit target" that is the best realistic price (not a profit, just a less-bad exit) and sell into any strength that approaches it.

**Hard floor:** If position value drops below 15% of total invested AND it's Q4, sell everything at market. Don't ride to zero.

**IMPORTANT:** Defensive mode does NOT apply when the position is profitable. If you're up and it's Q4, you're still in the house money system, not defensive mode. Defensive mode is specifically for managing losing positions late in the game.

---

## 9. EXIT LOGIC (All Strategies)

### Conservative Strategy Exits
1. Up 30% → sell 50%
2. Up 60% → sell remaining 50%. Done.
3. Down 30% AND held 12+ min AND deficit growing → sell all
4. Deficit > 25 AND Q3+ AND < 8 min remaining → sell all
5. Game ends → settlement

### Tiered Strategy Exits (House Money System)

**Before capital recovery:**
- At 1.75x (75% gain): sell 40% of all shares. This approximately recovers your total cost basis across all entries. Mark as "capital recovered."
- Stop loss: governed by game mode (see Section 8). No price-based stop in offensive mode.

**After capital recovery (house money mode):**
- At 3x gain from average cost: sell 25% of remaining shares
- At 5x gain: sell 30% of remaining shares
- At 80¢+ with < 3 minutes left: sell 60% of remaining shares
- Let final shares ride to settlement ($1.00 potential)
- Trailing stop: if price drops 50% from highest price reached → sell all remaining

**Defensive mode exits (when underwater late):**
- Sell into any scoring run / price uptick
- Hard floor: value < 15% of invested in Q4 → sell all

### Heavy Favorite Collapse Exits

**More patient than Tiered** because we expect the team to likely win.

**Before capital recovery:**
- At 2x (100% gain): sell 35% of all shares. Higher threshold than Tiered because conviction is higher.
- Stop loss: same game mode system as Tiered.

**After capital recovery:**
- At 3x: sell 20% of remaining
- At 60¢+: sell 20% of remaining
- Let rest ride to settlement (we EXPECT this team to win)
- Trailing stop: 40% from peak → sell all remaining

**Defensive mode:** Same as Tiered.

---

## 10. INJURY DETECTION & RESPONSE

### Detection Methods (v1)

**Method 1: Play-by-play absence (3-5 minute detection)**
Monitor NBA CDN play-by-play feed. Maintain a list of top-3 players by minutes for each team (pre-loaded from BallDontLie or static lookup, updated monthly). If a top-3 player hasn't appeared in any play-by-play event for 5+ minutes of game time, flag as "POTENTIAL_INJURY." This is our early warning.

**Method 2: Official NBA injury report (10-15 minute confirmation)**
Use the `nbainjuries` Python package to check NBA.com's official injury report page. When a player is officially listed as "out for remainder" or "will not return," this is CONFIRMED. Poll every 2-3 minutes during active positions.

**Neither method is instant.** We accept a 5-15 minute delay for v1. If the model proves profitable, we can add faster detection (Twitter API, paid injury feeds) in v2.

### Response Rules

**Step 1: Classify team star depth.**

Maintain a lookup table:

- **Single-star teams:** One player dramatically more important than the rest. Examples: Jokic (Nuggets), Luka (Mavs), Giannis (Bucks). If their star goes down, the team's comeback ability drops dramatically.

- **Multi-star teams:** Two or three stars sharing the load. Examples: Tatum + Brown (Celtics), Curry + Green (Warriors). Losing one hurts but doesn't break the team.

Update this list monthly. It's ~30 entries and doesn't change often.

**Step 2: Response based on team depth + player importance.**

| Situation | Action |
|-----------|--------|
| Star injured on single-star team | Immediately shift to defensive mode. Sell 50% on any price uptick. If confirmed out, sell remaining 50%. |
| Star injured on multi-star team | Shift to defensive mode regardless of quarter. Do NOT auto-sell. Monitor for 5 minutes. If remaining stars step up and deficit shrinks, shift back to neutral. If deficit grows, begin exiting. |
| Non-star injured (role player, bench) | No action. Does not affect thesis. |
| Star on OPPOSING team injured | Good for us. Hold. Do not add to position solely based on opponent injury. |
| Multiple stars on our team injured | Sell 75% immediately. Rare scenario but devastating. |

---

## 11. RISK MANAGEMENT

### Per-Strategy Limits
| Rule | Conservative | Tiered | Heavy Favorite |
|------|-------------|--------|----------------|
| Daily loss limit | 15% of strategy bankroll | 15% | 15% |
| Weekly loss limit | 25% of strategy bankroll | 25% | 25% |
| Max concurrent positions | 2 | 3 | 2 |
| Max per game (with nuclear) | 8% | 24% | 36% (with spread multiplier) |

### Global Limits
- **Total bankroll hard floor:** If total across all strategies drops below 60% of starting bankroll, EVERYTHING pauses. Full review before resuming.
- **No trading in final 2 minutes:** Prices are volatile, liquidity dries up, outcomes are mostly decided.
- **Always check market status:** Before any action, verify Kalshi market status == "open."

### Order Execution Safety
- Always use limit orders (never market orders — Kalshi spreads can be wide)
- Before every entry, check order book depth at intended price
- If our order would consume > 30% of visible liquidity at our price level, reduce size or skip
- Track slippage for every trade. If average slippage > 3¢, investigate execution logic.

---

## 12. DASHBOARD SPECIFICATION (6 Tabs)

Technology: FastAPI backend + inline HTML/JS/CSS frontend. Chart.js for charts. Auto-refreshes every 10 seconds.

### Live Games Panel (always visible at top of every tab)
For every game being monitored, show:
- Teams, score, quarter, time remaining
- Pre-game spread
- Kalshi bid / ask / last price
- Kalshi tipoff price and price drop %
- Fair value (from Odds API) and edge
- Deficit vs spread
- Signal status: which strategies (if any) have signals on this game
- Position status: do we have a position, and in which strategy

### Tab 1: Overview
- Total bankroll and P&L across all three strategies
- Per-strategy cards: balance, P&L (today + total + %), win rate, active positions
- Combined P&L chart: three lines (one per strategy) plotted over time
- Comparison table: every metric side by side for all three strategies
- Today's stats: signals fired vs trades taken (opportunities seen vs acted on)

### Tab 2: Conservative Strategy Detail
- Balance, P&L, win rate, avg win, avg loss, best trade, worst trade
- **Edge analysis chart:** Win rate bucketed by edge size (8-10%, 10-12%, 12%+). Bar chart.
- **Entry analysis:** Win rate by deficit size, by quarter, by entry price level
- **Exit analysis:** How each trade ended — take profit 1, take profit 2, stop loss, settlement win, settlement loss. Pie chart.
- Average hold time for winners vs losers
- "Left on table" analysis: trades exited at TP2 where price kept rising
- Active position cards: entry price, current price, fair value, edge, P&L, time held, exit targets
- Trade history table: sortable by time, team, entry price, exit price, P&L, edge, deficit, quarter

### Tab 3: Tiered Strategy Detail
- Balance, P&L, win rate, avg win, avg loss, best trade, worst trade
- **Multi-entry analysis:** How often Entry 2/3/4 were used. Win rate comparison: single entry vs multiple entries. Average cost basis improvement from averaging down.
- **House money tracker:** How many trades reached capital recovery. Average additional gain after recovery. Table of all house-money trades with entry→exit paths.
- **Game mode analysis:** How often positions ended in defensive mode. Average loss in defensive mode vs average total loss (did defensive mode help?)
- **Price drop analysis:** Win rate by price drop at Entry 1 (25-35%, 35-45%, 45%+). Bar chart.
- **Deficit analysis:** Win rate by deficit at entry (10-12, 12-15, 15-18, 18+). Bar chart.
- **Time analysis:** Win rate by quarter and time remaining at first entry
- Active positions: house money status, current mode (offensive/neutral/defensive), next exit targets, all entry points shown
- Trade history with multi-entry detail

### Tab 4: Heavy Favorite Collapse Detail
- Balance, P&L, win rate
- **Spread analysis:** Win rate bucketed by pre-game spread (8-10, 10-12, 12+). This tells us if the spread confidence multiplier is working.
- **Settlement rate:** % of trades that went to full settlement ($1.00) vs exited early
- **Position sizing analysis:** Average P&L for 1x vs 1.25x vs 1.5x sized trades
- **Multi-entry analysis:** Same as Tiered tab
- **Time analysis:** Same as Tiered tab
- Active positions and trade history

### Tab 5: Comparison & Insights
- Head-to-head table: all three strategies on every metric
- **Factor analysis across ALL strategies:**
  - Win rate by quarter of entry
  - Win rate by day of week
  - Win rate by home vs away favorite
  - Win rate by spread range
  - Win rate by number of entries (1 vs 2 vs 3+)
- **Correlation analysis:** Do all three strategies win/lose on the same nights?
- **Position sizing recommendations:** Kelly criterion calculations based on actual results
- **Auto-generated insights:** Plain English recommendations. Examples:
  - "Conservative has 92% win rate when edge > 12%. Consider raising min edge."
  - "Tiered loses money on Q3 entries. Restrict to Q1-Q2."
  - "Heavy Favorite with spread > 12 has never lost. Increase allocation."
- **Export button:** Download all trades, signals, game snapshots as CSV

### Tab 6: Signal Log (debugging + optimization)
- Every signal generated by every strategy, whether traded or not
- Why signals were passed: "edge only 6%", "order book too thin", "max positions reached"
- **Missed opportunities:** Signals we passed that would have been winners
- **Bad entries:** Signals we took that were losers
- Filter by strategy, date range, outcome (win/loss/skipped)
- This tab is critical for tuning parameters after each week of trading

---

## 13. DATABASE SCHEMA

### Table: trades
Stores every buy and sell action. Immutable log.
```
trade_id, timestamp, game_id, kalshi_ticker, team, strategy, action,
entry_number, price_cents, shares, total_cents, pnl_cents, reason,
game_quarter, game_time_remaining, score_home, score_away,
deficit_vs_spread, fair_value, edge, price_drop_pct, orderbook_depth,
game_mode
```

### Table: positions
Current state of all positions (active and closed).
```
position_id, game_id, kalshi_ticker, team, strategy,
total_shares, total_cost_cents, avg_cost_cents, entry_count,
game_budget_used, nuclear_budget_used,
shares_remaining, status, capital_recovered, capital_recovered_amount,
highest_price_cents, current_mode,
realized_pnl_cents, created_at, updated_at
```

### Table: entries
Individual entry records for multi-entry tracking.
```
entry_id, position_id, entry_number, timestamp,
quarter, time_remaining, price_cents, shares, cost_cents, reason
```

### Table: game_snapshots
Logged every 30 seconds per live game. This is the gold mine for analysis.
```
id, timestamp, game_id, kalshi_ticker,
home_team, away_team, home_score, away_score,
quarter, time_remaining, game_status,
opening_spread, current_spread, fair_value_home, fair_value_away,
kalshi_yes_bid, kalshi_yes_ask, kalshi_last_price,
kalshi_volume, kalshi_book_depth,
deficit_vs_spread, edge, price_drop_pct, momentum_score
```

### Table: signals
Every signal generated, whether acted on or not.
```
id, timestamp, game_id, team, strategy, signal_type,
entry_number, deficit, edge, price_drop_pct, kalshi_price,
confidence, reason, action_taken, skip_reason
```

### Table: daily_performance
End-of-day summary per strategy.
```
id, date, strategy,
starting_balance, ending_balance, pnl_cents,
trades_count, wins, losses, best_trade, worst_trade,
avg_win, avg_loss
```

### Table: injury_events
Log of all detected injury flags.
```
id, timestamp, game_id, player_name, team,
detection_method, confirmed, severity,
action_taken, position_affected, position_id
```

---

## 14. FILE STRUCTURE

```
nba-trading-bot/
├── .env                           # API keys (gitignored)
├── .env.example                   # Template with all required keys
├── requirements.txt               # Python dependencies
├── run.py                         # Entry point: python run.py
│
├── core/
│   ├── __init__.py
│   ├── config.py                  # All configuration + strategy parameters
│   ├── models.py                  # All dataclasses (Section 3)
│   ├── database.py                # SQLite ORM + all logging functions
│   └── bot.py                     # Main loop orchestrator
│
├── data/
│   ├── __init__.py
│   ├── kalshi_client.py           # Kalshi API v2 with RSA auth
│   ├── espn_client.py             # ESPN scoreboard + NBA CDN fallback
│   ├── odds_client.py             # The Odds API + fair value calculation
│   ├── aggregator.py              # Merges all sources → LiveGameState
│   ├── injury_detector.py         # Play-by-play absence + nbainjuries package
│   └── team_names.py              # Team name normalization across all APIs
│
├── strategies/
│   ├── __init__.py
│   ├── base.py                    # Base strategy class + common logic
│   ├── conservative.py            # Conservative strategy (Section 4)
│   ├── tiered.py                  # Tiered strategy (Section 5)
│   └── heavy_favorite.py          # Heavy Favorite Collapse (Section 6)
│
├── trading/
│   ├── __init__.py
│   ├── paper_engine.py            # Paper trading with real prices
│   ├── live_engine.py             # Real order execution (Week 4+)
│   ├── position_manager.py        # Multi-entry tracking + exits + modes
│   └── risk_manager.py            # All limits, kill switches, safety checks
│
├── dashboard/
│   ├── __init__.py
│   ├── app.py                     # FastAPI app with all API endpoints
│   └── templates.py               # HTML/JS/CSS for all 6 tabs
│
├── alerts/
│   ├── __init__.py
│   └── telegram.py                # Telegram notifications (optional)
│
├── data_files/
│   ├── star_players.json          # Top 3 players per team + depth classification
│   └── team_name_map.json         # Canonical name mappings across APIs
│
├── db/
│   └── trading_bot.db             # SQLite database (auto-created)
│
└── logs/
    └── bot.log                    # Rotating log file
```

### requirements.txt
```
requests>=2.31.0
fastapi>=0.104.0
uvicorn>=0.24.0
sqlalchemy>=2.0.0
python-dotenv>=1.0.0
cryptography>=41.0.0
pytz>=2023.3
nbainjuries>=0.1.0
python-telegram-bot>=20.0
```

### .env.example
```
# Kalshi (required)
KALSHI_API_KEY_ID=your-api-key-id
KALSHI_PRIVATE_KEY_PATH=./kalshi-key.pem
KALSHI_ENV=demo

# The Odds API (required)
ODDS_API_KEY=your-key-here

# Telegram (optional)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Settings
PAPER_TRADING=true
INITIAL_BALANCE=500
LOG_LEVEL=INFO
```

---

## 15. PHASE 1 (WEEK 1): Foundation + Paper Trading

### Goal: Bot runs during live NBA games, uses real data from all APIs, simulates trades, logs everything.

**Build in this order:**

1. `core/config.py` — All parameters for all three strategies
2. `core/models.py` — All dataclasses
3. `data/team_names.py` — Team name normalization (test against all 30 NBA teams)
4. `data/kalshi_client.py` — Connect to Kalshi DEMO API with RSA auth. Verify you can fetch markets and prices.
5. `data/espn_client.py` — Fetch live scores. Parse quarter, time, scores. Handle "pre", "in", "post" states. Add NBA CDN fallback.
6. `data/odds_client.py` — Connect to The Odds API. Calculate fair value. Track quota usage.
7. `data/aggregator.py` — Merge all sources into LiveGameState per game.
8. `core/database.py` — Create all tables. Implement all logging functions.
9. `strategies/` — Implement all three strategies with entry checks and exit logic.
10. `trading/position_manager.py` — Multi-entry tracking, mode management, exit execution.
11. `trading/paper_engine.py` — Check real orderbook depth, simulate fills at real prices.
12. `trading/risk_manager.py` — All limits and safety checks.
13. `core/bot.py` — Main loop tying everything together.
14. `run.py` — Entry point.

**Do NOT build the dashboard in Week 1.** Focus on the core engine. Use SQLite queries and log output to verify the bot is working.

**Week 1 success criteria:**
- Bot connects to all four APIs (Kalshi demo, ESPN, NBA CDN, Odds API)
- LiveGameState objects are correctly populated during live games
- Strategies generate signals based on real data
- Paper trades are executed at real Kalshi prices with orderbook depth checks
- Every game snapshot, signal, and trade is logged to SQLite
- Bot runs for a full night of NBA games without crashing

---

## 16. PHASE 2 (WEEK 2): Production Kalshi + Fair Value Refinement

### Goal: Switch to real Kalshi production data. Refine parameters using Week 1 data.

1. Switch Kalshi base URL to production (`trading-api.kalshi.com`)
2. Still paper trading — just using real production prices (better liquidity)
3. Query Week 1 database to analyze:
   - What deficit sizes actually triggered signals?
   - What edges existed? Were they real?
   - What Kalshi price levels are most profitable?
   - Did multi-entry averaging help or hurt?
4. Adjust parameters based on data:
   - Maybe min_deficit should be 14 not 12
   - Maybe min_edge should be 10% not 8%
   - Maybe Q3 entries never work and should be disabled
5. Implement opening price tracking (track Kalshi price at market open AND at tipoff)
6. Build `data/injury_detector.py` — play-by-play absence + nbainjuries package

---

## 17. PHASE 3 (WEEK 3): Dashboard + Advanced Signals + Optimization

### Goal: Visual dashboard for analysis. Advanced signal features. Position sizing optimization.

1. Build full 6-tab dashboard (Section 12)
2. Add momentum detection from play-by-play data (scoring runs)
3. Add order book imbalance tracking (bid depth vs ask depth ratio)
4. Implement Kelly Criterion position sizing based on actual results
5. Analyze 2+ weeks of data for all three strategies
6. Answer the key question: **Is this system profitable on paper?**
7. If yes → prepare for live trading in Week 4
8. If no → identify what's not working from dashboard data and iterate

---

## WHAT MAKES THIS DIFFERENT FROM THE OLD BOT

| Old Bot | New Bot |
|---------|---------|
| Kalshi prices are random numbers | Real Kalshi API with RSA auth |
| Fair value is `0.55 - deficit * 0.02` | Vegas consensus from The Odds API |
| One entry per game | Up to 4 entries with averaging down |
| Flat stop loss at -30% | Time-based modes (offensive/neutral/defensive) |
| Two strategies with similar logic | Three distinct strategies for different setups |
| No spread awareness | Spread drives strategy selection and sizing |
| Database exists but never used | Every data point logged to SQLite |
| No liquidity checks | Orderbook depth verified before every entry |
| No game-end handling | Markets settle, positions resolve correctly |
| Single-page dashboard | 6-tab dashboard with deep analytics |
| No injury handling | Play-by-play absence + official report + team depth awareness |

---

**This document is complete and self-contained. Start with Phase 1 and build each component in the order specified. Do not skip to the dashboard before the core engine works.**
