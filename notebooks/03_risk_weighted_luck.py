"""Experiment 03 — Risk-weighted luck.

Question: does pricing a lucky call by its blast radius separate
agent modes that the plain Luck Rate calls identical?

Method:
  1. Per-mode separation: 200 traces of each mock mode, mean per-run
     risk score and luck rate per mode.
  2. Per-tier uninformed rates on the headline 200-trace dataset
     (40% lucky injected, 10% fail, seed 7).
  3. Correlation: per-run Pearson between the lucky indicator (0/1)
     and the per-run risk score on the headline dataset; plus the
     sweep-level correlation between Luck Rate and RWLS across
     injected lucky rates 0.0-0.8.
  4. Weight sensitivity: recompute the per-mode scores under two
     other plausible weight maps and check the mode ordering is
     unchanged.

Run from the repo root: python notebooks/03_risk_weighted_luck.py
Writes: results/risk_weighted_luck.csv, results/risk_weighted_luck.json
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from luck_audit.audit import aggregate, audit_trace
from luck_audit.mock import MODES, generate_dataset, generate_trace
from luck_audit.risk import pearson
from luck_audit.schema import BOOKING_TOOLS, specs_by_name


def _score_with_weights(audits, weights: dict[str, float]) -> list[float | None]:
    """Per-run risk scores under an alternative weight map.

    Recomputed from the ledgers (not the core) so the experiment can
    vary the policy without touching the shipped defaults.
    """
    specs = specs_by_name(list(BOOKING_TOOLS))
    scores: list[float | None] = []
    for audit in audits:
        total = 0.0
        lucky = 0.0
        for ledger in audit.ledgers:
            spec = specs.get(ledger.tool)
            tier = spec.risk_tier if spec is not None else "reversible"
            weight = weights[tier]
            total += weight
            if ledger.is_lucky:
                lucky += weight
        scores.append(lucky / total if total else None)
    return scores


def main() -> None:
    # 1. Per-mode separation (n=200 per mode).
    mode_rows = []
    for mode in MODES:
        traces = [generate_trace(f"{mode}-{i:03d}", mode, seed=7 + i) for i in range(200)]
        audits = [audit_trace(t) for t in traces]
        metrics = aggregate(audits, traces)
        scores = [a.risk_score for a in audits if a.risk_score is not None]
        mode_rows.append(
            {
                "mode": mode,
                "n": len(traces),
                "successful_runs": metrics.successful_runs,
                "luck_rate": (
                    round(metrics.luck_rate, 4)
                    if metrics.luck_rate is not None
                    else None
                ),
                "mean_risk_score": (
                    round(sum(scores) / len(scores), 4) if scores else None
                ),
                "risk_weighted_luck_score": (
                    round(metrics.risk_weighted_luck_score, 4)
                    if metrics.risk_weighted_luck_score is not None
                    else None
                ),
            }
        )
        print(mode_rows[-1])

    # 2 + 3a. Headline dataset: per-tier rates and per-run correlation.
    traces = generate_dataset(n=200, lucky_rate=0.4, wrong_rate=0.1, seed=7)
    audits = [audit_trace(t) for t in traces]
    metrics = aggregate(audits, traces)
    per_run = pearson(
        [1.0 if a.is_lucky else 0.0 for a in audits],
        [a.risk_score if a.risk_score is not None else 0.0 for a in audits],
    )
    print(f"headline: luck_rate={metrics.luck_rate:.4f} "
          f"rwls={metrics.risk_weighted_luck_score:.4f}")
    print(f"per-tier uninformed rates: {metrics.uninformed_rate_by_tier}")
    print(f"per-run Pearson(lucky indicator, risk score) = {per_run:.4f}")

    # 3b. Sweep-level correlation across injected lucky rates.
    sweep_luck: list[float] = []
    sweep_rwls: list[float] = []
    for injected in (0.0, 0.2, 0.4, 0.6, 0.8):
        sweep_traces = generate_dataset(
            n=200, lucky_rate=injected, wrong_rate=0.1, seed=7
        )
        sweep_metrics = aggregate(
            [audit_trace(t) for t in sweep_traces], sweep_traces
        )
        sweep_luck.append(sweep_metrics.luck_rate or 0.0)
        sweep_rwls.append(sweep_metrics.risk_weighted_luck_score or 0.0)
    sweep_corr = pearson(sweep_luck, sweep_rwls)
    print(f"sweep-level Pearson(luck rate, RWLS) = {sweep_corr:.4f}")
    print(f"sweep luck rates: {[round(v, 3) for v in sweep_luck]}")
    print(f"sweep RWLS: {[round(v, 3) for v in sweep_rwls]}")

    # 4. Weight sensitivity: does the mode ordering survive other
    # plausible weights? (default 3/1/0.25; alternatives 2/1/0.25
    # and 5/1/0.5; flat 1/1/1 is the plain uninformed-call rate.)
    demo_audits = [audit_trace(t) for t in
                   [generate_trace(f"demo-{m}", m, seed=42) for m in MODES]]
    sensitivity = {}
    for label, weights in {
        "default 3/1/0.25": {"irreversible": 3.0, "reversible": 1.0, "low": 0.25},
        "mild 2/1/0.25": {"irreversible": 2.0, "reversible": 1.0, "low": 0.25},
        "steep 5/1/0.5": {"irreversible": 5.0, "reversible": 1.0, "low": 0.5},
        "flat 1/1/1": {"irreversible": 1.0, "reversible": 1.0, "low": 1.0},
    }.items():
        scores = _score_with_weights(demo_audits, weights)
        sensitivity[label] = {
            mode: (round(score, 4) if score is not None else None)
            for mode, score in zip(MODES, scores)
        }
        print(f"{label}: {sensitivity[label]}")

    out = {
        "per_mode": mode_rows,
        "headline": {
            "luck_rate": metrics.luck_rate,
            "risk_weighted_luck_score": metrics.risk_weighted_luck_score,
            "uninformed_rate_by_tier": metrics.uninformed_rate_by_tier,
            "risk_weight_by_tier": metrics.risk_weight_by_tier,
            "lucky_weight": metrics.lucky_weight,
            "total_weight": metrics.total_weight,
            "per_run_pearson_lucky_vs_risk": per_run,
        },
        "sweep": {
            "luck_rates": sweep_luck,
            "risk_weighted_scores": sweep_rwls,
            "pearson": sweep_corr,
        },
        "weight_sensitivity_demo_modes": sensitivity,
    }
    csv_out = ROOT / "results" / "risk_weighted_luck.csv"
    with open(csv_out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(mode_rows[0]))
        writer.writeheader()
        writer.writerows(mode_rows)
    json_out = ROOT / "results" / "risk_weighted_luck.json"
    json_out.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {csv_out} and {json_out}")


if __name__ == "__main__":
    main()
