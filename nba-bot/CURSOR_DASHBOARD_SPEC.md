# CURSOR: Dashboard Frontend Specification

## YOUR TASK
Build `dashboard/templates.py` — a single function `render_dashboard()` that returns one HTML string with embedded CSS and JS. The backend API already exists at `dashboard/app.py`. You are ONLY building the frontend.

## TECH STACK
- Single HTML page with embedded `<style>` and `<script>` tags
- Chart.js (CDN: https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js)
- No React, no build tools — pure HTML/CSS/JS
- Auto-refresh every 10 seconds via `setInterval` + `fetch()`
- Dark theme (dark gray background, white text, colored accents)

## API ENDPOINTS (all return JSON)

```
GET /api/status
→ {running, loop_count, mode, risk: {global_pause, strategy_pauses, bankrolls, total_bankroll, positions_count}, live_games: [...], active_positions: [...], odds_quota: {remaining, used}}

GET /api/trades?strategy=CONSERVATIVE&limit=100
→ [{trade_id, timestamp, position_id, game_id, team, strategy, action, entry_number, price_cents, shares, total_cents, pnl_cents, reason, game_quarter, game_time_remaining, deficit_vs_spread, fair_value, edge, price_drop_pct, orderbook_depth, game_mode}, ...]

GET /api/signals?strategy=TIERED&limit=200
→ [{signal_id, timestamp, game_id, team, strategy, signal_type, entry_number, deficit, edge, price_drop_pct, kalshi_price, pre_game_spread, confidence, reason, action_taken, skip_reason}, ...]

GET /api/positions/active
→ [{position_id, game_id, team, strategy, total_shares, total_cost_cents, avg_cost_cents, entry_count, shares_remaining, status, capital_recovered, highest_price_cents, current_mode}, ...]

GET /api/performance?days=30
→ [{date, strategy, starting_balance_cents, ending_balance_cents, pnl_cents, trades_count, wins, losses, best_trade_cents, worst_trade_cents, avg_win_cents, avg_loss_cents}, ...]

GET /api/stats/{strategy}
→ {total_trades, wins, losses, win_rate, total_pnl, avg_win, avg_loss, best_trade, worst_trade}
(strategy = CONSERVATIVE, TIERED, or HEAVY_FAVORITE)

GET /api/snapshots/{game_id}
→ [{timestamp, game_id, home_score, away_score, quarter, time_remaining, kalshi_yes_ask, kalshi_yes_bid, deficit_vs_spread, edge, price_drop_pct, fair_value_home}, ...]
```

## PAGE LAYOUT

### Top Bar (always visible)
- Bot status indicator: green dot if running, red if paused
- Mode badge: "PAPER" or "LIVE"
- Total bankroll: "$XXX.XX"
- Odds API quota: "XXX/500 remaining"
- Loop count
- Auto-refresh countdown

### Live Games Panel (always visible, below top bar)
Horizontal scrollable row of game cards. One card per game. Each card shows:
- Team names + scores (large font)
- Quarter + clock: "Q2 6:42"
- Spread: "-5.5"
- Kalshi price: "Bid: 28¢ / Ask: 32¢"
- Price drop from tipoff: "-45%"  (red text)
- Fair value: "41%"
- Edge: "+9%" (green if positive)
- Deficit vs spread: "15.5"
- Book depth: "234 contracts"
- Signal indicator: colored dots for which strategies have signals (blue=conservative, green=tiered, orange=heavy favorite)
- Position indicator: if we have a position, show strategy name + entry count + mode badge

Color coding: card border is green if we have a profitable position, red if losing, gray if no position.

### Tab Navigation
6 tabs below the live games panel. Tab content fills remaining page height.

### Tab 1: Overview
**Left column (60%):**
- Three strategy cards side by side:
  - Strategy name + colored header (blue/green/orange)
  - Current balance
  - Today's P&L (green/red)
  - Total P&L
  - Win rate (big number)
  - Active positions count
  - Paused indicator if kill switch active

- Combined P&L Chart (Chart.js line chart):
  - X-axis: date
  - Three lines: one per strategy, color-coded
  - Pull data from /api/performance

**Right column (40%):**
- Today's Activity Feed: recent trades and signals as a scrollable list
  - Each item: timestamp, strategy badge, team, action, price, P&L
  - Color code: green for wins, red for losses, gray for entries

- Comparison table:
  |  | Conservative | Tiered | Heavy Fav |
  |--|--|--|--|
  | Win Rate | 67% | 52% | 71% |
  | Avg Win | $X | $X | $X |
  | Avg Loss | $X | $X | $X |
  | Best Trade | $X | $X | $X |
  | Worst Trade | $X | $X | $X |
  | Total P&L | $X | $X | $X |

### Tab 2: Conservative Detail
- Stats row: balance, P&L, win rate, avg win, avg loss, trades count
- **Edge Analysis** (bar chart): win rate bucketed by edge (8-10%, 10-12%, 12%+). Calculate from trades data where strategy=CONSERVATIVE.
- **Entry Analysis** (bar chart): win rate by deficit bucket (12-15, 15-18, 18-20, 20+)
- **Exit Breakdown** (pie chart): count of trades by exit reason (TP1, TP2, stop loss, settlement win, settlement loss)
- **Active Positions** table: each row = one position with entry price, current price, P&L, edge at entry, time held
- **Trade History** table: sortable columns — date, team, entry price, exit price, P&L, edge, deficit, quarter, reason. Paginated.

### Tab 3: Tiered Detail
- Stats row (same format as Tab 2)
- **Multi-Entry Analysis** (bar chart): win rate for 1-entry vs 2-entry vs 3+ entry trades. Also show avg P&L for each bucket.
- **House Money Tracker**: table of trades that reached capital recovery. Show: entry cost, recovery amount, additional proceeds after recovery, final result.
- **Game Mode Analysis** (pie chart): how many positions ended in each mode (offensive exit, neutral exit, defensive exit, settlement)
- **Price Drop Analysis** (bar chart): win rate by price drop bucket at entry (25-35%, 35-45%, 45%+)
- **Time Analysis** (bar chart): win rate by quarter of FIRST entry (Q1 vs Q2)
- **Active Positions** with mode badge (OFFENSIVE/NEUTRAL/DEFENSIVE), entry details, house money status
- **Trade History** with multi-entry detail: show all entries as sub-rows under each position

### Tab 4: Heavy Favorite Detail
- Same layout as Tab 3, plus:
- **Spread Analysis** (bar chart): win rate by pre-game spread bucket (8-10, 10-12, 12+)
- **Settlement Rate**: what % of trades went to $1.00 settlement vs exited early
- **Position Sizing Analysis**: avg P&L for 1x vs 1.25x vs 1.5x spread-multiplied trades

### Tab 5: Comparison & Insights
- Head-to-head table: all three strategies on every metric
- **Factor Analysis Charts** (multiple bar charts):
  - Win rate by quarter of entry (across all strategies)
  - Win rate by spread range
  - Win rate by number of entries
  - Win rate by day of week
- **Correlation**: do strategies win/lose on the same nights? Simple table showing overlap.
- **Auto-Insights**: Scan the data and generate plain English recommendations. Display as card elements.
  - Logic: If conservative win rate > 80% when edge > 12%, show "Conservative has X% win rate at 12%+ edge — consider raising minimum."
  - If tiered loses money on Q3 entries, show "Tiered loses on Q3 entries — restrict to Q1-Q2."
  - If heavy favorite with spread > 12 always wins, show "Heavy Favorite at 12+ spread has never lost."
  - These are calculated client-side from the trades data.
- **Export Button**: Download all trades as CSV. Use JS to convert trades JSON to CSV and trigger download.

### Tab 6: Signal Log
- Filterable table of ALL signals from /api/signals
- Filters: strategy dropdown, date range, outcome (traded/skipped/would-have-won/would-have-lost)
- Columns: timestamp, strategy, team, signal type, deficit, edge, price drop, kalshi price, spread, confidence, action taken (yes/no), skip reason
- Color code rows: green if traded and won, red if traded and lost, yellow if skipped but would have won (missed opportunity), gray if skipped and would have lost
- Summary stats at top: "Today: X signals fired, Y traded, Z skipped. Of skipped, W would have been winners."

## STYLE GUIDE
- Background: #1a1a2e
- Cards: #16213e with 1px border #0f3460
- Text: #e0e0e0
- Accent colors: Conservative = #4fc3f7 (blue), Tiered = #66bb6a (green), Heavy Favorite = #ffa726 (orange)
- Positive P&L: #4caf50
- Negative P&L: #ef5350
- Font: system-ui, -apple-system, sans-serif
- Border radius: 8px on cards
- Tables: alternating row colors, sticky headers
- Charts: dark background, grid lines at 20% opacity

## IMPLEMENTATION NOTES
- `render_dashboard()` returns ONE big HTML string. Use Python f-strings or triple-quoted strings.
- All data fetching happens client-side via `fetch()` calls to /api/* endpoints.
- On page load, fetch /api/status and populate everything.
- `setInterval(refreshData, 10000)` to auto-refresh.
- Tab switching is pure CSS/JS — hide/show div sections.
- Charts update on refresh without full page reload.
- Helper function to format cents to dollars: `(cents / 100).toFixed(2)`
- Helper to format timestamps: `new Date(ts).toLocaleString()`
- Handle empty states gracefully: "No trades yet", "No active positions", etc.
- Mobile-friendly is NOT required. Desktop-only is fine.
