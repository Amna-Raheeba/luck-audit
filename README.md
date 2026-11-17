# Luck Audit

> A benchmark can report 95% success while half the passes were guesses. This tool audits an agent's trace after the run and reports the share of successful runs that were lucky, not competent: every mutating tool call is checked for whether each of its required arguments can be traced to evidence the agent actually observed — or whether the agent guessed and got away with it.

**Author:** Amna Raheeba · Companion to my evaluation platform ([ai-evaluation-platform](https://github.com/Amna-Raheeba/ai-evaluation-platform)), which scores outcomes, and my guardrail middleware ([explainable-guardrail-middleware](https://github.com/Amna-Raheeba/explainable-guardrail-middleware)), which blocks bad actions live. This one audits good outcomes after the fact.

---

## 1. Overview

### 1.1 The problem

Agent benchmarks report success rates. A success hides a second
question: did the agent *know* what it was doing? A booking agent that
books the right flight without ever seeing the flight number did not
succeed — it got lucky. The closest prior work, "Near-Miss: Latent
Policy Failure Detection in Agentic Workflows" (arXiv 2603.29665),
finds that 8–17% of successful τ²-bench Airlines trajectories contain
latent policy failures — but it is policy-based and tied to one
benchmark and one domain. Nothing audits *evidence sufficiency* in a
policy-free, domain-general way.

### 1.2 The idea

A **policy-free evidence-sufficiency provenance ledger**. For each
mutating call, every required argument is traced to the earliest trace
span that supplied it — a user message, a tool result, a declared
system fact, or a chained argument from an earlier evidenced call — or
marked `uninformed`. The headline metric is the **Luck Rate**: the
share of successful runs with at least one uninformed mutating call.

### 1.3 What it is not

- Not a policy checker. It does not know whether an action was
  allowed, only whether the agent had the evidence to choose it.
- Not a replay. It audits the recorded trace; it does not re-run the
  agent. If the trace omits a tool result, arguments that depended on
  it read as uninformed — the ledger is honest about what the trace
  shows.
- Not a model. No LLM call, no embedding, no GPU. Stdlib-only,
  deterministic, fully offline.

## 2. How It Works

### 2.1 The evidence rule

| Source | Counts as evidence? |
|---|---|
| User message | Yes — the value appears in what the user typed |
| Tool result | Yes — exact structured field, or inside the result text |
| Declared system fact | Yes — a constant declared up front (e.g. today's date) |
| Chained argument | Yes — equals an earlier call's argument that was itself evidenced |
| Agent's own reasoning | **No** — a value the model merely thought about is not evidence |
| Final answer | **No** — it comes after the call, so it cannot have informed it |

### 2.2 Verdicts

| Verdict | Meaning |
|---|---|
| `competent` | Run succeeded and every mutating call is fully evidenced |
| `lucky` | Run succeeded but ≥1 mutating call has an uninformed required argument |
| `failed` | Run itself failed — luck is not assessed |

### 2.3 Example

```python
from luck_audit import audit_trace
from luck_audit.trace import read_traces

audit = audit_trace(read_traces("examples/demo_trace.jsonl")[0])
print(audit.verdict)  # lucky
for ledger in audit.ledgers:
    for entry in ledger.entries:
        print(entry.arg, entry.status, entry.source_kind)
```

```text
lucky
flight_id uninformed None
passenger_name evidenced user
seat uninformed None
hotel_id evidenced tool_result
...
```

## 3. Measured Results

All numbers from real runs on 2026-11-17, mock booking world, seed 7.
Nothing here is estimated.

### 3.1 Headline (n=200, 40% lucky, 10% fail)

- **Luck Rate: 48.6%** — 85 of 175 successful runs were lucky
- Competent success rate: 45.0% (vs a naive success rate of 87.5%)
- Uninformed-call rate: 29.3% (110 of 375 mutating calls)
- Auditor vs injected ground truth (1,300 labelled args):
  **precision 100%, recall 100%, accuracy 100%**

### 3.2 Luck-rate sweep (n=200 per point)

| Injected lucky rate | Measured luck rate | Auditor accuracy |
|---|---|---|
| 0.0 | 0.0% | 100.0% |
| 0.2 | 26.3% | 100.0% |
| 0.4 | 48.6% | 100.0% |
| 0.6 | 70.9% | 100.0% |
| 0.8 | 90.9% | 100.0% |

The measured rate runs above the injected rate because the injected
rate is a share of *all* traces while the measured rate is a share of
*successful* traces — the 10% that fail leave the denominator.

### 3.3 The thought rule is load-bearing (ablation)

| Variant | Luck rate | Auditor accuracy |
|---|---|---|
| Strict (thoughts are not evidence) | 48.6% | 100.0% |
| Loose (thoughts count as evidence) | 0.0% | 89.5% |

The loose variant misses every lucky pass: the lucky agent's thoughts
name the guessed flight and seat, so counting thoughts as evidence
launders every guess.

### 3.4 Uninformed rate by argument (n=200)

`book_flight.seat` 40.5% · `book_flight.flight_id` 25.5% ·
`book_hotel.hotel_id` 16.6% · names and dates 0.0% — the identifiers
the agent must look up are the ones it guesses; what the user stated
is never uninformed.

### 3.5 Risk-weighted luck (new in v0.2.0)

The plain Luck Rate counts a guessed flight and a guessed hotel the
same way — one lucky run each. But their blast radii differ: a flight
booking charges a non-refundable fare the moment it is made, while a
hotel booking can usually be cancelled free of charge. No auditor
prices that difference, so this one does: every mutating tool carries
a declared risk tier (`irreversible` ×3.0, `reversible` ×1.0,
`low` ×0.25), and the **Risk-Weighted Luck Score** is the risk weight
of lucky mutating calls divided by the risk weight of all mutating
calls, over successful runs.

- **Aggregate RWLS: 28.1%** vs a plain Luck Rate of 48.6% — the
  lucky weight is 197.0 of 700.0 total (irreversible calls carry 75%
  of the weight).
- Per-tier uninformed rates: **irreversible 32.0%**, reversible 16.6%.
- Per-mode separation (n=200 per mode): competent **0.00**,
  lucky_flight **0.75**, lucky_seat **0.75**, lucky_hotel **0.25** —
  while the plain luck rate is 1.00 for all three lucky modes.
- The score is not a rescaled luck rate: per-run Pearson between the
  lucky indicator and the risk score is **0.46** on the 200-trace
  dataset, while the sweep-level correlation is 0.9999 (both rise
  together as more runs are lucky, but the risk score stays lower).
- Honest limit: the tiers and weights are a *declared policy*, not a
  measured quantity. The ordering (flight/seat guesses worse than
  hotel guesses) is unchanged under milder (×2) and steeper (×5)
  weights, and collapses — as it should — under flat weights, which
  proves the weights do the work. See `docs/metrics.md` §6.

## 4. Quickstart

```bash
git clone https://github.com/Amna-Raheeba/luck-audit.git
cd luck-audit
python -m luck_audit demo        # audit one trace per agent mode
python -m luck_audit generate --n 200 --lucky 0.4 --seed 7 --out traces.jsonl
python -m luck_audit audit traces.jsonl --report report.md
streamlit run dashboard/app.py   # dashboard (pip install streamlit)
```

No dependencies for the core library — Python 3.10+ only.

## 5. Auditing Your Own Tools

Declare your tools with `ToolSpec` — nothing about the auditor is
booking-specific:

```python
from luck_audit import audit_trace
from luck_audit.schema import ToolSpec
from luck_audit.trace import read_traces

specs = [
    ToolSpec("send_payment", mutating=True, required_args=("amount", "payee_iban")),
    ToolSpec("get_balance", mutating=False),
]
audit = audit_trace(read_traces("my_traces.jsonl")[0], specs=specs)
```

## 6. Repository Map

```text
luck_audit/        core: trace, schema, matching, provenance, audit, mock,
                   report, risk (risk-weighted luck), CLI
tests/             80 pytest tests (plain `pytest`, bare venv)
dashboard/         Streamlit app + pure helpers over the real pipeline
                   (4 tabs incl. risk-weighted luck)
notebooks/         01 luck-rate sweep · 02 matching-sensitivity ablation ·
                   03 risk-weighted luck
scripts/           reproduce_results.py — regenerates every results file
                   in one command and checks the headline numbers
examples/          a lucky trace + a script that audits it
docs/              architecture · api · metrics · experiment_log
results/           sweep CSVs, metrics JSON, summary report
```

## 7. Limitations

- The mock world is small and the lucky modes are caricatures; the
  numbers prove the auditor works on this world, not on real agent
  traffic. The honest next step is running it on real traces
  (τ²-bench, AgentDojo, or your own logs) — the CLI takes any JSONL
  trace file in the documented format.
- Matching is conservative by design: a value that is paraphrased
  rather than repeated verbatim reads as uninformed. That is a
  false-positive risk on messy real traces, and it is disclosed here
  rather than tuned away.
- The risk tiers and weights are declared policy, not measured
  quantities. A deployer who prices blast radius differently declares
  their own tiers in `ToolSpec` — the score follows the declaration,
  and the sensitivity analysis in `docs/metrics.md` §6 shows what
  changes when the weights do.
