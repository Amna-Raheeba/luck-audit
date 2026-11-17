# API

## 1. Core functions

```python
from luck_audit import audit_trace, aggregate
from luck_audit.trace import read_traces
from luck_audit.mock import generate_dataset

traces = read_traces("traces.jsonl")
audits = [audit_trace(t) for t in traces]
metrics = aggregate(audits, traces)
print(metrics.luck_rate)          # lucky successful runs / successful runs
print(metrics.auditor_accuracy)   # vs injected ground truth, when present
```

## 2. `audit_trace(trace, specs=BOOKING_TOOLS) -> RunAudit`

Audits one trace. `specs` is a dict or sequence of `ToolSpec`. Returns
a `RunAudit` with `.verdict` (`competent` / `lucky` / `failed`),
`.ledgers` (one `CallLedger` per mutating call), and
`.evidence_coverage` (evidenced required args / all required args).

## 3. `aggregate(audits, traces=None) -> AggregateMetrics`

Aggregates run audits. Pass the traces as well to score the auditor
against injected ground truth (`auditor_precision`, `auditor_recall`,
`auditor_accuracy`, `ground_truth_calls`). Fields:

| Field | Meaning |
|---|---|
| `luck_rate` | lucky runs / successful runs (None if no successes) |
| `competent_success_rate` | competent runs / all runs |
| `uninformed_call_rate` | lucky mutating calls / all mutating calls |
| `uninformed_rate_by_tool` | per-tool lucky-call rate |
| `uninformed_rate_by_arg` | per-argument uninformed rate |
| `auditor_precision` / `recall` / `accuracy` | vs ground truth |

## 4. `EvidenceLedger(specs).build(trace) -> list[CallLedger]`

The per-call ledger. Each `CallLedger` has `.is_lucky`,
`.uninformed_args`, `.evidence_coverage`, and `.entries` — one
`ArgProvenance` per required argument with `.status`
(`evidenced` / `uninformed`), `.source_kind` (`user` / `system` /
`tool_result` / `chained`), `.source_event_id`, `.source_field`.

## 5. `ToolSpec(name, mutating, required_args=())`

Declare your own tools. Only mutating tools are audited; only
required arguments are traced. Read-only tools are never audited as
calls, but their results are evidence.

## 6. Mock generation

```python
from luck_audit.mock import generate_trace, generate_dataset, demo_traces

trace = generate_trace("run-001", "lucky_seat", seed=5)  # modes: competent,
# lucky_flight, lucky_seat, lucky_hotel, wrong_flight
traces = generate_dataset(n=200, lucky_rate=0.4, wrong_rate=0.1, seed=7)
```

## 7. CLI

```bash
python -m luck_audit demo
python -m luck_audit generate --n 100 --lucky 0.4 --seed 7 --out traces.jsonl
python -m luck_audit audit traces.jsonl --report report.md --json report.json
python -m luck_audit experiment --n 200 --seed 7 --out sweep.json
```

## 8. Risk-weighted luck

```python
from luck_audit import audit_trace, aggregate, risk_weight
from luck_audit.mock import generate_dataset

traces = generate_dataset(n=200, lucky_rate=0.4, seed=7)
audits = [audit_trace(t) for t in traces]
metrics = aggregate(audits, traces)
print(metrics.risk_weighted_luck_score)   # 0.2814
print(metrics.uninformed_rate_by_tier)    # {"irreversible": 0.32, ...}
print(audits[0].risk_score)               # per-run score, or None
```

- `ToolSpec(..., risk_tier="irreversible")` — declare a tool's
  blast-radius tier: `"irreversible"` (×3.0), `"reversible"` (×1.0),
  or `"low"` (×0.25). Defaults: `"reversible"` for mutating tools,
  `"low"` otherwise. Unknown tiers raise.
- `risk_weight(tier) -> float` — the weight of one tier.
- `run_risk_score(ledgers, specs=BOOKING_TOOLS) -> float | None` —
  per-run score; None when the run made no mutating calls.
- `aggregate_risk(audits, specs=BOOKING_TOOLS) -> dict` — aggregate
  score over successful runs, per-tier uninformed rates, and per-tier
  weight shares, plus the raw lucky/total weights.
- `RunAudit.risk_score` and `AggregateMetrics.risk_weighted_luck_score`
  / `uninformed_rate_by_tier` / `risk_weight_by_tier` /
  `lucky_weight` / `total_weight` are included in `to_dict()` and in
  both report formats. The CLI prints the aggregate score with the
  other metrics.
