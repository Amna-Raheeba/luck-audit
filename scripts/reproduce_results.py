"""Reproduce every number in results/ from scratch, in one command.

Run from the repo root:

    python scripts/reproduce_results.py

Regenerates (all deterministic, seed 7):
  - results/traces_200.jsonl        the headline 200-trace dataset
    (generated data; git-ignored, never pushed)
  - results/summary.md             markdown report of the headline run
  - results/metrics.json           aggregate metrics ONLY (small on
    purpose: the full per-run JSON report is regenerable from the
    traces file with `python -m luck_audit audit
    results/traces_200.jsonl --json full_report.json`)
  - results/luck_rate_sweep.csv    experiment 01
  - results/matching_sensitivity.csv  experiment 02
  - results/risk_weighted_luck.csv / .json  experiment 03

Exits non-zero if any headline number differs from the values
documented in README.md and docs/metrics.md, so a silent drift is
caught instead of shipped.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from luck_audit.audit import aggregate, audit_trace
from luck_audit.mock import generate_dataset
from luck_audit.report import markdown_report
from luck_audit.trace import write_traces

# Headline numbers, as documented in README.md / docs/metrics.md.
EXPECTED = {
    "total_runs": 200,
    "successful_runs": 175,
    "lucky_runs": 85,
    "luck_rate": 85 / 175,
    "risk_weighted_luck_score": 197 / 700,
}


def main() -> int:
    results = ROOT / "results"
    results.mkdir(exist_ok=True)

    traces = generate_dataset(n=200, lucky_rate=0.4, wrong_rate=0.1, seed=7)
    write_traces(traces, results / "traces_200.jsonl")
    audits = [audit_trace(t) for t in traces]
    metrics = aggregate(audits, traces)

    (results / "summary.md").write_text(
        markdown_report(metrics, audits), encoding="utf-8"
    )
    # Metrics only — the full per-run report (metrics + all 200 run
    # ledgers) is ~600 KB, too large for the connector push path and
    # regenerable from traces_200.jsonl at any time.
    (results / "metrics.json").write_text(
        json.dumps(metrics.to_dict(), indent=2), encoding="utf-8"
    )

    # Run the experiment notebooks exactly as CI runs them.
    for notebook in (
        "01_luck_rate_experiment.py",
        "02_matching_sensitivity.py",
        "03_risk_weighted_luck.py",
    ):
        subprocess.run(
            [sys.executable, str(ROOT / "notebooks" / notebook)],
            check=True,
            cwd=ROOT,
        )

    errors = []
    for key, expected in EXPECTED.items():
        actual = getattr(metrics, key)
        if isinstance(expected, float):
            ok = abs(actual - expected) < 1e-9
        else:
            ok = actual == expected
        if not ok:
            errors.append(f"{key}: got {actual!r}, expected {expected!r}")
    if errors:
        print("MISMATCH — documented numbers drifted:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("All headline numbers match the documented values.")
    print(f"luck rate {metrics.luck_rate:.1%}, "
          f"risk-weighted luck score "
          f"{metrics.risk_weighted_luck_score:.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
