"""Example: audit a single recorded trace and print its ledger.

Run from the repo root:
    python examples/audit_a_trace.py examples/demo_trace.jsonl
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from luck_audit.audit import audit_trace
from luck_audit.trace import read_traces


def main() -> None:
    path = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "examples" / "demo_trace.jsonl")
    traces = read_traces(path)
    for trace in traces:
        audit = audit_trace(trace)
        print(f"{trace.run_id}: outcome={trace.outcome} verdict={audit.verdict}")
        for ledger in audit.ledgers:
            for entry in ledger.entries:
                source = entry.source_kind or "none"
                print(f"  {ledger.tool}.{entry.arg} = {entry.value!r}: "
                      f"{entry.status} (source: {source})")


if __name__ == "__main__":
    main()
