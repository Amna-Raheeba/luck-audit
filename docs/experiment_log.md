# Experiment Log

## 2026-11-17 — v0.1.0 build

### Demo (5 traces, one per mode)

- competent → competent, coverage 100%
- lucky_flight → lucky (flight_id + seat uninformed), coverage 71%
- lucky_seat → lucky (seat uninformed), coverage 86%
- lucky_hotel → lucky (hotel_id uninformed), coverage 86%
- wrong_flight → failed (booking error), coverage 33%
- Demo luck rate 75.0% (3 of 4 successes); auditor 100% on 31 labels.

### Experiment 01 — luck-rate sweep (notebooks/01)

n=200 per point, seed 7, 10% wrong. Measured luck rate tracks the
injected rate monotonically (0.0% / 26.3% / 48.6% / 70.9% / 90.9%),
auditor accuracy 100.0% at every point. Results in
`results/luck_rate_sweep.csv`.

### Experiment 02 — matching sensitivity (notebooks/02)

Same 200 traces, strict vs loose (thoughts relabelled as user
messages). Strict: luck rate 48.6%, accuracy 100.0%. Loose: luck rate
0.0%, accuracy 89.5%. The thought rule is load-bearing. Results in
`results/matching_sensitivity.csv`.

### Experiment 03 — risk-weighted luck (notebooks/03, v0.2.0)

Question: does pricing a lucky call by blast radius separate modes
the plain Luck Rate calls identical? Answer: yes. Per-mode means
(n=200 per mode): competent 0.00, lucky_flight 0.75, lucky_seat 0.75,
lucky_hotel 0.25 — plain luck rate 1.00 for all three lucky modes.
Headline dataset: RWLS 28.1% vs luck rate 48.6%; per-tier
uninformed rates irreversible 32.0%, reversible 16.6%. Per-run
Pearson(lucky, risk) = 0.46 (the score adds information beyond the
binary verdict); sweep-level Pearson = 0.9999 (both rise together).
Weight sensitivity: mode ordering stable under 2/1 and 5/1 weights;
flat weights collapse all lucky modes to 0.50, proving the weights
do the work. Results in `results/risk_weighted_luck.csv` / `.json`.

### Bugs found by tests during the build

1. Date-in-text matching missed written dates ("5 Dec 2026" did not
   match the argument "2026-12-05"). Fixed by scanning the span for
   date-like substrings and comparing parsed dates.
2. Mock test assumed `call-1` is always the booking call; in modes
   that search first, the booking is `call-2`/`call-3`. Fixed by
   looking the call id up from the trace events.
3. First mock design made lucky_flight always fail (guessed seat 12A
   was not on the plane). Fixed by guessing a valid but unobserved
   seat (16C) and by removing seats from search summaries, so a
   guessed seat is genuinely uninformed.
