# Architecture

## 1. Design in one paragraph

Luck Audit takes a recorded agent trace and a declaration of which
tools mutate the world, and returns a per-call provenance ledger plus a
run verdict. It is a pure function of the trace: no model, no network,
no randomness, no policy. The same trace always produces the same
ledger.

## 2. Modules

| Module | Responsibility |
|---|---|
| `trace.py` | The trace model: ordered events, validation, JSONL I/O. Ground truth lives here but the auditor never reads it. |
| `schema.py` | `ToolSpec`: which tools are mutating and which arguments are decision-critical. The one place a deployer declares facts about their own tools. |
| `matching.py` | Conservative value matching: normalised equality for numbers, dates, and text; substring matching inside free text with a minimum length of 3. |
| `provenance.py` | `EvidenceLedger`: traces each required argument to its earliest evidence span, or marks it uninformed. |
| `audit.py` | Run verdicts (`competent` / `lucky` / `failed`) and aggregate metrics, including auditor accuracy vs injected ground truth. |
| `mock.py` | Deterministic mock booking world + mock agent with five modes; generates traces with injected ground truth. |
| `report.py` | Markdown and JSON reports from an audit run. |
| `risk.py` | Risk-weighted luck: per-run and aggregate scores, per-tier rates, Pearson correlation. Pure functions over ledgers. |
| `__main__.py` | CLI: `demo`, `generate`, `audit`, `experiment`. |

## 3. The evidence rule

For a mutating call at position *i*, a required argument is evidenced
if its value appears in an earlier span of one of these kinds, checked
in this order:

1. **System fact** — a constant declared up front in the trace
   (e.g. today's date). Timeless, checked first.
2. **User message** — the value appears in what the user typed.
3. **Tool result** — the value appears as an exact structured field,
   or inside the result text.
4. **Chained** — the value equals an argument of an earlier tool call
   whose own argument was itself evidenced.

Two kinds of span are **never** evidence:

- **Thought** — the agent's own reasoning. A value the model merely
  thought about is not evidence; that is the whole point of the audit.
  Experiment 02 shows this rule is load-bearing: counting thoughts as
  evidence drops the measured luck rate from 48.6% to 0.0% on the same
  dataset.
- **Final answer** — it comes after the call, so it cannot have
  informed it. Evidence must precede the call it justifies.

## 4. Risk tiers

A mutating tool's `risk_tier` (declared in its `ToolSpec`) prices the
blast radius of a lucky call: `irreversible` (×3.0 — the effect cannot
be undone without a second mutating call or a real-world cost),
`reversible` (×1.0 — cleanly undoable), `low` (×0.25 — trivially
correctable). The booking schema declares `book_flight` irreversible
(the fare is charged at once, typically non-refundable),
`book_hotel` reversible (free cancellation inside its window), and
`cancel_booking` irreversible. The weights are declared policy, not
measured quantities; `risk.py` computes the score from whatever tiers
the deployer declares, and the sensitivity analysis in
`docs/metrics.md` §6.3 shows the mode ordering survives other
plausible weights. The plain Luck Rate ignores tiers entirely.

## 5. Verdicts

- `failed` — the run itself failed. Luck is not assessed.
- `lucky` — the run succeeded and at least one mutating call has an
  uninformed required argument.
- `competent` — the run succeeded and every mutating call is fully
  evidenced.

## 6. What it is not

- Not a policy checker. It does not know whether an action was
  allowed; it knows whether the agent had the evidence to choose it.
  The closest prior work, "Near-Miss" (arXiv 2603.29665), finds latent
  *policy* failures in successful τ²-bench Airlines trajectories.
  Luck Audit is policy-free and domain-general: it audits evidence
  sufficiency for any mutating tool in any domain.
- Not a replay. It audits the recorded trace; it does not re-run the
  agent. If the trace is incomplete (a tool result omitted), arguments
  that depended on it will read as uninformed — the ledger is honest
  about what the trace shows, and the report says so.
- Not a detector of wrong outcomes. A lucky run's outcome was right.
  That is precisely the failure mode benchmarks miss when they report
  success rates alone.
