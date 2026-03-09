#!/usr/bin/env python3
"""Generate an intelligent weekly strategy scorecard from exports.

Usage:
  python tools/weekly_scorecard.py \
    --trades trades_export.csv \
    --positions positions_export.csv \
    --out-md docs/weekly_scorecard.md \
    --out-json docs/weekly_scorecard.json
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Tuple


@dataclass
class BucketStats:
    n_positions: int = 0
    pnl_cents: int = 0
    wins: int = 0
    losses: int = 0
    avg_win_cents: float = 0.0
    avg_loss_cents: float = 0.0
    profit_factor: float = 0.0
    expectancy_cents: float = 0.0


def spread_bucket(spread: float) -> str:
    if spread <= 3.5:
        return "<=3.5"
    if spread < 8:
        return "3.5-8"
    return ">=8"


def hold_bucket(minutes: float) -> str:
    if minutes < 20:
        return "<20m"
    if minutes < 60:
        return "20-60m"
    return ">=60m"


def _safe_float(v: str, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _safe_int(v: str, default: int = 0) -> int:
    try:
        return int(v)
    except Exception:
        return default


def load_trades(path: Path) -> List[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def build_position_rollup(trades: List[dict]) -> Dict[str, dict]:
    rollup: Dict[str, dict] = {}
    for t in trades:
        pid = t["position_id"]
        if pid not in rollup:
            rollup[pid] = {
                "strategy": t["strategy"],
                "entries": 0,
                "pnl_cents": 0,
                "spread": None,
                "first_quarter": None,
                "edge": None,
                "first_ts": t["timestamp"],
                "last_ts": t["timestamp"],
                "stopped": False,
                "later_recovered": False,
            }
        r = rollup[pid]
        r["last_ts"] = t["timestamp"]

        if t["action"] == "BUY":
            r["entries"] = max(r["entries"], _safe_int(t.get("entry_number") or "1", 1))
            if r["first_quarter"] is None:
                r["first_quarter"] = _safe_int(t.get("game_quarter") or "0")
            if r["edge"] is None and t.get("edge"):
                r["edge"] = _safe_float(t.get("edge"), 0.0)
            if r["spread"] is None:
                reason = t.get("reason", "")
                marker = "spread="
                if marker in reason:
                    try:
                        rest = reason.split(marker, 1)[1]
                        r["spread"] = float(rest.split(",", 1)[0])
                    except Exception:
                        pass

        if t["action"].startswith("SELL") and t.get("pnl_cents"):
            pnl = _safe_int(t["pnl_cents"], 0)
            r["pnl_cents"] += pnl
            reason = (t.get("reason") or "").lower()
            if "stop" in reason:
                r["stopped"] = True
            if pnl > 0 and r["stopped"]:
                r["later_recovered"] = True

    return rollup


def summarize_positions(rollup: Dict[str, dict]) -> Tuple[Dict[str, BucketStats], Dict[str, BucketStats], Dict[str, BucketStats]]:
    by_strategy: Dict[str, List[int]] = defaultdict(list)
    by_spread: Dict[str, List[int]] = defaultdict(list)
    by_entries: Dict[str, List[int]] = defaultdict(list)

    for r in rollup.values():
        pnl = r["pnl_cents"]
        by_strategy[r["strategy"]].append(pnl)
        if r["spread"] is not None:
            by_spread[spread_bucket(float(r["spread"]))].append(pnl)
        e = r["entries"]
        k = "1" if e == 1 else "2" if e == 2 else "3+"
        by_entries[k].append(pnl)

    def _stats(items: List[int]) -> BucketStats:
        if not items:
            return BucketStats()
        wins = [x for x in items if x > 0]
        losses = [x for x in items if x < 0]
        gross_win = sum(wins)
        gross_loss = -sum(losses)
        return BucketStats(
            n_positions=len(items),
            pnl_cents=sum(items),
            wins=len(wins),
            losses=len(losses),
            avg_win_cents=(statistics.mean(wins) if wins else 0.0),
            avg_loss_cents=(-statistics.mean(losses) if losses else 0.0),
            profit_factor=(gross_win / gross_loss if gross_loss else 0.0),
            expectancy_cents=(sum(items) / len(items)),
        )

    return (
        {k: _stats(v) for k, v in by_strategy.items()},
        {k: _stats(v) for k, v in by_spread.items()},
        {k: _stats(v) for k, v in by_entries.items()},
    )


def governance_recommendations(by_spread: Dict[str, BucketStats], by_entries: Dict[str, BucketStats]) -> List[str]:
    recs: List[str] = []

    close = by_spread.get("<=3.5")
    if close and close.n_positions >= 5 and close.expectancy_cents < 0:
        recs.append(
            "Close-spread bucket expectancy is negative with meaningful sample; keep scalp-only regime, cap entries at 2, reduce sizing 25%."
        )

    e3 = by_entries.get("3+")
    if e3 and e3.n_positions >= 3 and e3.expectancy_cents < 0:
        recs.append(
            "3+ entry bucket is negative; tighten Entry-3 gate and reduce nuclear reserve allocation."
        )

    if not recs:
        recs.append("No automatic throttles triggered; keep parameters stable for one more week to avoid overfitting.")

    return recs


def write_markdown(out: Path, by_strategy: Dict[str, BucketStats], by_spread: Dict[str, BucketStats], by_entries: Dict[str, BucketStats], recs: List[str]):
    def row(name: str, s: BucketStats) -> str:
        wr = (s.wins / s.n_positions * 100) if s.n_positions else 0
        return (
            f"| {name} | {s.n_positions} | {wr:.1f}% | ${s.pnl_cents/100:.2f} | "
            f"${s.expectancy_cents/100:.2f} | {s.profit_factor:.2f} | "
            f"${s.avg_win_cents/100:.2f} | ${s.avg_loss_cents/100:.2f} |"
        )

    lines = [
        "# Weekly Strategy Scorecard",
        "",
        "## By Strategy",
        "| Strategy | Positions | Win Rate | Net PnL | Expectancy/Pos | Profit Factor | Avg Win | Avg Loss |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for k in sorted(by_strategy):
        lines.append(row(k, by_strategy[k]))

    lines.extend([
        "",
        "## By Spread Bucket",
        "| Spread Bucket | Positions | Win Rate | Net PnL | Expectancy/Pos | Profit Factor | Avg Win | Avg Loss |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for k in ["<=3.5", "3.5-8", ">=8"]:
        if k in by_spread:
            lines.append(row(k, by_spread[k]))

    lines.extend([
        "",
        "## By Entry Count Bucket",
        "| Entry Count | Positions | Win Rate | Net PnL | Expectancy/Pos | Profit Factor | Avg Win | Avg Loss |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ])
    for k in ["1", "2", "3+"]:
        if k in by_entries:
            lines.append(row(k, by_entries[k]))

    lines.extend(["", "## Governance Recommendations"])
    for r in recs:
        lines.append(f"- {r}")

    out.write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trades", default="trades_export.csv")
    ap.add_argument("--positions", default="positions_export.csv")
    ap.add_argument("--out-md", default="docs/weekly_scorecard.md")
    ap.add_argument("--out-json", default="docs/weekly_scorecard.json")
    args = ap.parse_args()

    trades = load_trades(Path(args.trades))
    rollup = build_position_rollup(trades)
    by_strategy, by_spread, by_entries = summarize_positions(rollup)
    recs = governance_recommendations(by_spread, by_entries)

    write_markdown(Path(args.out_md), by_strategy, by_spread, by_entries, recs)

    payload = {
        "by_strategy": {k: asdict(v) for k, v in by_strategy.items()},
        "by_spread": {k: asdict(v) for k, v in by_spread.items()},
        "by_entry_bucket": {k: asdict(v) for k, v in by_entries.items()},
        "recommendations": recs,
    }
    Path(args.out_json).write_text(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
