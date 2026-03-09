# Four-Phase Strategy Implementation (Paper Trading)

This document captures the productionized architecture implemented for:
1. Regime-aware strategy behavior
2. Payoff-shape / risk-geometry controls
3. Intelligent weekly scorecard and governance recommendations
4. Walk-forward paper-trading protocol before live money

## Phase 1 — Regime-aware strategy architecture

### Tiered V2
- Spread `<= 3.5` is treated as **close-spread scalp**.
  - Max entries: 2
  - Targets are average-entry-relative (`avg + 6c`, `avg + 10c` with ceiling)
  - Tight stop and earlier time stop in Q3
- Spread `> 3.5` remains recovery-oriented with stricter gating for Entry 3+.

### Tiered Classic
- Kept for A/B comparison but reconfigured with reachable multipliers (`1.5x`, `2.0x`, `2.2x`).
- Entry 3+ blocked unless spread is sufficiently strong.

### Conservative
- Entry edge threshold is now regime-aware:
  - higher minimum edge in close-spread games
  - moderate minimum edge in mid-spread games

### Heavy Favorite
- Entry 3+ restricted to stronger spread games.

---

## Phase 2 — Payoff-shape / risk-geometry controls

Implemented hard tail-loss controls across strategies:
- Tiered: universal per-position max-loss cap
- Tiered recovery mode (3+ entries): explicit hard stop
- Tiered Classic: universal cap + recovery hard stop
- Heavy Favorite: universal per-position max-loss cap

This addresses the core geometry problem where large, averaged-down positions could remain open for breakeven-only outcomes while losses continued to expand.

---

## Phase 3 — Intelligent weekly scorecard

New tool: `tools/weekly_scorecard.py`

### Inputs
- `trades_export.csv`
- `positions_export.csv` (reserved for future enrichment)

### Outputs
- `docs/weekly_scorecard.md` (human-readable report)
- `docs/weekly_scorecard.json` (structured for dashboards/automation)

### Metrics computed
- By strategy: win rate, net PnL, expectancy/position, profit factor, avg win/loss
- By spread bucket: `<=3.5`, `3.5-8`, `>=8`
- By entry-count bucket: `1`, `2`, `3+`

### Governance recommendations
The tool emits automatic recommendations when performance degrades in key buckets, including:
- reducing close-spread sizing,
- tightening Entry-3 gates,
- reducing nuclear reserve exposure.

---

## Phase 4 — Walk-forward paper-trading protocol

1. Run one full week with fixed parameters.
2. Generate scorecard and recommendations.
3. Modify only one parameter family at a time.
4. Validate changes out-of-sample in the next week.
5. Promote to live only after sustained positive expectancy with controlled drawdowns.

### Suggested acceptance gates before real money
- 4+ paper weeks with positive total expectancy
- No single bucket (spread or 3+ entries) responsible for >40% of losses
- Profit factor > 1.15 overall and > 1.0 in close-spread bucket
- Max weekly drawdown within predefined risk budget

