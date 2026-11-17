"""Dashboard helpers: pure functions, no Streamlit import.

Kept separate from app.py so the logic is unit-tested (see
tests/test_dashboard_helpers.py) and the dashboard is a thin view over
the real pipeline, not a second implementation of it.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Usable from the repo root and from inside dashboard/ alike.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from luck_audit.audit import aggregate, audit_trace
from luck_audit.mock import demo_traces, generate_dataset


def audit_demo() -> list[dict]:
    """Audit one trace per mode; return one summary dict per run."""
    rows = []
    for trace in demo_traces():
        audit = audit_trace(trace)
        rows.append(
            {
                "run_id": trace.run_id,
                "outcome": trace.outcome,
                "verdict": audit.verdict,
                "mutating_calls": audit.mutating_calls,
                "lucky_calls": audit.lucky_calls,
                "evidence_coverage": round(audit.evidence_coverage, 2),
            }
        )
    return rows


def ledger_rows(run_id: str) -> list[dict]:
    """Full per-argument ledger rows for one demo run."""
    for trace in demo_traces():
        if trace.run_id != run_id:
            continue
        audit = audit_trace(trace)
        rows = []
        for ledger in audit.ledgers:
            for entry in ledger.entries:
                rows.append(
                    {
                        "tool": ledger.tool,
                        "arg": entry.arg,
                        "value": str(entry.value),
                        "status": entry.status,
                        "source": entry.source_kind or "-",
                        "source_event": entry.source_event_id or "-",
                    }
                )
        return rows
    raise ValueError(f"unknown demo run {run_id!r}")


def risk_demo() -> list[dict]:
    """Per-mode risk scores for the demo traces.

    The plain verdict calls all three lucky modes "lucky"; the risk
    score separates the irreversible guess (flight, 0.75) from the
    reversible one (hotel, 0.25).
    """
    rows = []
    for trace in demo_traces():
        audit = audit_trace(trace)
        rows.append(
            {
                "run_id": trace.run_id,
                "mode": trace.run_id.removeprefix("demo-"),
                "outcome": trace.outcome,
                "verdict": audit.verdict,
                "risk_score": (
                    round(audit.risk_score, 2)
                    if audit.risk_score is not None
                    else None
                ),
            }
        )
    return rows


def sweep_summary(n: int = 100, seed: int = 7) -> list[dict]:
    """Measured luck rate at injected lucky rates 0.0–0.8."""
    rows = []
    for lucky_rate in (0.0, 0.2, 0.4, 0.6, 0.8):
        traces = generate_dataset(n=n, lucky_rate=lucky_rate, wrong_rate=0.1, seed=seed)
        metrics = aggregate([audit_trace(t) for t in traces], traces)
        rows.append(
            {
                "injected_lucky_rate": lucky_rate,
                "measured_luck_rate": (
                    round(metrics.luck_rate, 3) if metrics.luck_rate is not None else None
                ),
                "successful_runs": metrics.successful_runs,
                "lucky_runs": metrics.lucky_runs,
                "auditor_accuracy": (
                    round(metrics.auditor_accuracy, 3)
                    if metrics.auditor_accuracy is not None
                    else None
                ),
            }
        )
    return rows


def dataset_metrics(n: int = 200, lucky_rate: float = 0.4, seed: int = 7) -> dict:
    """Aggregate metrics for a generated dataset, as plain data."""
    traces = generate_dataset(n=n, lucky_rate=lucky_rate, wrong_rate=0.1, seed=seed)
    metrics = aggregate([audit_trace(t) for t in traces], traces)
    return metrics.to_dict()
