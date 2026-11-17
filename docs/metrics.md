# Metrics

All numbers below are measured on 2026-11-17 with the mock booking
world in this repo (seed 7 unless stated). Nothing here is estimated.

## 1. Definitions

| Metric | Definition |
|---|---|
| Luck Rate | Successful runs with ≥1 uninformed mutating call / all successful runs. The headline number. |
| Competent success rate | Fully evidenced successful runs / all runs. What a success rate *should* have been. |
| Uninformed-call rate | Mutating calls with ≥1 uninformed required arg / all mutating calls. |
| Uninformed rate by tool / by arg | The same rate, broken down per tool and per argument. |
| Auditor precision / recall / accuracy | The auditor's own labels vs the injected ground truth recorded by the trace generator. |

## 2. Headline results (n=200, lucky 0.4, wrong 0.1, seed 7)

- Runs: 200 (175 success, 25 failed)
- Lucky runs: 85 · Competent runs: 90
- **Luck Rate: 48.6%** — nearly half of the "successful" runs were lucky
- Competent success rate: 45.0% (vs a naive success rate of 87.5%)
- Mutating calls: 375 (110 lucky) — uninformed-call rate 29.3%
- Auditor vs ground truth (1,300 labelled args): **precision 100%,
  recall 100%, accuracy 100%**

## 3. Luck-rate sweep (n=200 per point, seed 7)

| Injected lucky rate | Measured luck rate | Auditor accuracy |
|---|---|---|
| 0.0 | 0.0% | 100.0% |
| 0.2 | 26.3% | 100.0% |
| 0.4 | 48.6% | 100.0% |
| 0.6 | 70.9% | 100.0% |
| 0.8 | 90.9% | 100.0% |

Note: the measured rate runs above the injected rate because the
injected rate is a share of *all* traces while the measured rate is a
share of *successful* traces — the 10% that fail outright leave the
denominator. At injected 0.4: 80 lucky traces of 175 successes is
45.7% before random-draw variation; measured 48.6%.

## 4. Matching sensitivity (ablation, same 200 traces)

| Variant | Luck rate | Auditor accuracy |
|---|---|---|
| Strict (thoughts are not evidence) | 48.6% | 100.0% |
| Loose (thoughts count as evidence) | 0.0% | 89.5% |

The loose variant misses every lucky pass: the lucky agent's thoughts
name the guessed flight and seat, so counting thoughts as evidence
launders every guess. The thought rule is load-bearing, not cosmetic.

## 5. Uninformed rate by argument (n=200 dataset)

The most-guessed arguments are the identifiers the agent must look
up: `book_flight.seat` and `book_flight.flight_id`, then
`book_hotel.hotel_id`. Names and dates — which come from the user
message — are never uninformed in this world. See
`results/summary.md` for the full per-argument table.

## 6. Risk-weighted luck (v0.2.0, experiment 03)

A lucky guess is not equally bad everywhere. Each mutating tool
carries a declared risk tier in its `ToolSpec` — `book_flight`
irreversible (×3.0: the fare is charged at once, typically
non-refundable), `book_hotel` reversible (×1.0: free cancellation
inside its window), `cancel_booking` irreversible (×3.0) — and the
Risk-Weighted Luck Score (RWLS) is the risk weight of lucky mutating
calls divided by the risk weight of all mutating calls, over
successful runs.

### 6.1 Per-mode separation (n=200 per mode, seed 7)

| Mode | Luck rate | Mean per-run risk score | Aggregate RWLS |
|---|---|---|---|
| competent | 0.00 | 0.00 | 0.00 |
| lucky_flight | 1.00 | 0.75 | 0.75 |
| lucky_seat | 1.00 | 0.75 | 0.75 |
| lucky_hotel | 1.00 | 0.25 | 0.25 |
| wrong_flight | n/a (0 successes) | 1.00 | n/a |

The plain luck rate is 1.00 for all three lucky modes; the risk score
separates the irreversible guess (0.75) from the reversible one
(0.25). The failed mode's per-run score is 1.00 (its one irreversible
call was lucky) but it never enters the aggregate, which — like the
Luck Rate — covers successful runs only.

### 6.2 Headline dataset (n=200, lucky 0.4, wrong 0.1, seed 7)

- **RWLS: 28.1%** vs Luck Rate 48.6% — lucky weight 197.0 of 700.0
- Per-tier uninformed rates: **irreversible 32.0%** (56 of 175
  flight bookings guessed), **reversible 16.6%** (29 of 175 hotel
  bookings guessed). Irreversible calls carry 75% of the total risk
  weight, so they dominate the score — which is the point.
- Per-run Pearson between the lucky indicator (0/1) and the per-run
  risk score: **0.46**. The risk score is not a rescaled luck rate:
  it carries information the binary verdict does not.
- Sweep-level Pearson between Luck Rate and RWLS across injected
  lucky rates 0.0–0.8: **0.9999** — both rise together (more lucky
  runs means more lucky weight), but RWLS stays below the luck rate
  at every point (0.151 vs 0.263; 0.281 vs 0.486; 0.417 vs 0.709;
  0.536 vs 0.909).

### 6.3 Weight sensitivity (demo modes)

| Weight map | competent | lucky_flight | lucky_seat | lucky_hotel |
|---|---|---|---|---|
| default 3 / 1 / 0.25 | 0.00 | 0.75 | 0.75 | 0.25 |
| mild 2 / 1 / 0.25 | 0.00 | 0.67 | 0.67 | 0.33 |
| steep 5 / 1 / 0.5 | 0.00 | 0.83 | 0.83 | 0.17 |
| flat 1 / 1 / 1 | 0.00 | 0.50 | 0.50 | 0.50 |

The ordering (flight/seat guesses worse than hotel guesses, both
worse than competent) is unchanged under milder and steeper weights.
Under flat weights all three lucky modes collapse to 0.50 — the
plain uninformed-call rate — which proves the weights, not the
ledger, do the separating. The honest limit stands: tiers and
weights are declared policy. A deployer who prices blast radius
differently declares their own tiers; the score follows.

## 7. What these numbers do and do not prove

- They prove the auditor works on this mock world: it recovers the
  injected ground truth exactly, and its headline metric tracks the
  injected lucky rate monotonically.
- They do **not** prove anything about real agent traffic. The mock
  world is small and the lucky modes are caricatures. The honest claim
  is: *if* your traces carry ground truth, the auditor will recover it;
  *if* your agents guess, the luck rate will show it. The next step is
  running it on real traces (τ²-bench, AgentDojo, or your own logs).
