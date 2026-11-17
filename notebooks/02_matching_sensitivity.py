"""Experiment 02 — Matching sensitivity: why thoughts are not evidence.

Question: how much does the "thoughts never count as evidence" rule
matter? Method: audit the same 200-trace dataset twice — once with the
real auditor, once with a loose variant in which every thought event
is relabelled as a user message (so anything the model "recalled" in
its reasoning counts as evidence). The lucky agent's thoughts name the
guessed flight and seat, so the loose variant should miss most lucky
passes.
Run from the repo root: python notebooks/02_matching_sensitivity.py
Writes: results/matching_sensitivity.csv
"""

from __future__ import annotations

import copy
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from luck_audit.audit import aggregate, audit_trace
from luck_audit.mock import generate_dataset


def relabel_thoughts_as_user(traces):
    """Return copies of the traces with thought events relabelled."""
    loose = []
    for trace in traces:
        clone = copy.deepcopy(trace)
        for event in clone.events:
            if event.kind == "thought":
                event.kind = "user"
        loose.append(clone)
    return loose


def main() -> None:
    traces = generate_dataset(n=200, lucky_rate=0.4, wrong_rate=0.1, seed=7)
    strict = aggregate([audit_trace(t) for t in traces], traces)
    loose_traces = relabel_thoughts_as_user(traces)
    loose = aggregate([audit_trace(t) for t in loose_traces], loose_traces)
    rows = [
        {
            "variant": "strict (thoughts are not evidence)",
            "luck_rate": round(strict.luck_rate, 4),
            "lucky_runs": strict.lucky_runs,
            "auditor_accuracy": round(strict.auditor_accuracy, 4),
        },
        {
            "variant": "loose (thoughts count as evidence)",
            "luck_rate": round(loose.luck_rate, 4),
            "lucky_runs": loose.lucky_runs,
            "auditor_accuracy": round(loose.auditor_accuracy, 4),
        },
    ]
    for row in rows:
        print(row)
    out = ROOT / "results" / "matching_sensitivity.csv"
    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
