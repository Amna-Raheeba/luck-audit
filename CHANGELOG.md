# Changelog

## 0.2.0 — 2026-11-17

- **Risk-weighted luck (new):** every mutating tool now declares a
  blast-radius tier in its `ToolSpec` — `irreversible` (×3.0),
  `reversible` (×1.0), `low` (×0.25) — and the Risk-Weighted Luck
  Score prices each lucky call by its tier (new module
  `luck_audit/risk.py`). The booking schema declares `book_flight`
  irreversible and `book_hotel` reversible. Measured: aggregate RWLS
  **28.1%** vs Luck Rate 48.6% on the 200-trace dataset; per-mode
  separation competent 0.00 / lucky_flight 0.75 / lucky_seat 0.75 /
  lucky_hotel 0.25 while the plain luck rate is 1.00 for all three
  lucky modes; per-tier uninformed rates irreversible 32.0%,
  reversible 16.6%; per-run Pearson(lucky, risk) 0.46,
  sweep-level 0.9999. Weight sensitivity: mode ordering stable under
  2/1 and 5/1 weights, collapses under flat weights as it should.
  Honest limit: tiers and weights are declared policy, not measured
  quantities. New experiment notebook 03, new dashboard tab, risk
  section in reports and CLI output.
- **Fix:** `results/metrics.json` was 592 KB (full per-run report)
  and would have failed the connector push (>100 KB). It now holds
  aggregate metrics only (1 KB); the full report is regenerable from
  `results/traces_200.jsonl` via the CLI.
- **Fix:** added `scripts/reproduce_results.py`, which regenerates
  every results file in one command and fails if any headline number
  drifts from the documented values. The `scripts/` directory was
  empty before this.
- **Fix:** replaced deprecated Streamlit `use_container_width` with
  `width="stretch"` (dashboard AppTest still 0 exceptions).
- 80 pytest tests (was 67), all passing; CI now also runs notebook 03
  and the reproduce script.

## 0.1.0 — 2026-11-17

First release.

- Policy-free, domain-general evidence-sufficiency provenance ledger:
  every required argument of every mutating call traced to its
  earliest evidence span (user message, tool result, declared system
  fact, chained evidenced argument) or marked `uninformed`. The
  agent's own reasoning and final answer never count as evidence.
- Run verdicts (`competent` / `lucky` / `failed`) and aggregate
  metrics: Luck Rate, competent success rate, uninformed-call rate
  per tool and per argument, plus auditor precision/recall/accuracy
  against injected ground truth.
- Deterministic mock booking world with five agent modes (competent,
  lucky_flight, lucky_seat, lucky_hotel, wrong_flight) and injected
  ground truth per call.
- Measured: Luck Rate 48.6% on a 200-trace dataset (40% lucky
  injected, 10% fail); sweep tracks the injected rate monotonically
  (0.0% / 26.3% / 48.6% / 70.9% / 90.9%); auditor 100% precision,
  recall, and accuracy on 1,300 labelled arguments. Ablation: counting
  thoughts as evidence collapses the luck rate to 0.0% — the thought
  rule is load-bearing.
- Streamlit dashboard over the real pipeline (demo traces, sweep,
  dataset metrics), verified with AppTest.
- 67 pytest tests, all passing; GitHub Actions CI (Python 3.10/3.11/3.12).
