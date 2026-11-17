"""Experiment 01 — Luck-rate sweep.

Question: does the measured luck rate track the injected lucky rate?
Method: generate n=200 traces at each injected lucky rate (0.0–0.8,
10% fail outright), audit them, record the measured luck rate and the
auditor's accuracy against injected ground truth.
Run from the repo root: python notebooks/01_luck_rate_experiment.py
Writes: results/luck_rate_sweep.csv
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from luck_audit.audit import aggregate, audit_trace
from luck_audit.mock import generate_dataset


def main() -> None:
    rows = []
    for lucky_rate in (0.0, 0.2, 0.4, 0.6, 0.8):
        traces = generate_dataset(n=200, lucky_rate=lucky_rate, wrong_rate=0.1, seed=7)
        metrics = aggregate([audit_trace(t) for t in traces], traces)
        rows.append(
            {
                "injected_lucky_rate": lucky_rate,
                "total_runs": metrics.total_runs,
                "successful_runs": metrics.successful_runs,
                "lucky_runs": metrics.lucky_runs,
                "luck_rate_measured": round(metrics.luck_rate, 4),
                "auditor_accuracy": round(metrics.auditor_accuracy, 4),
            }
        )
        print(
            f"injected {lucky_rate:.1f} -> measured luck rate "
            f"{metrics.luck_rate:.1%} (auditor accuracy {metrics.auditor_accuracy:.1%})"
        )
    out = ROOT / "results" / "luck_rate_sweep.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
