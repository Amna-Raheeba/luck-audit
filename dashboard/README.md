# Dashboard

A Streamlit dashboard over the real Luck Audit pipeline — it audits the
demo traces, runs the luck-rate sweep, and shows dataset metrics. It
imports `dashboard/helpers.py` (pure functions, unit-tested) and never
re-implements the audit.

## Run it

```bash
pip install streamlit
streamlit run dashboard/app.py
```

## Tabs

1. **Demo traces** — audit one trace per agent mode, inspect the
   per-argument provenance ledger of any run.
2. **Luck-rate sweep** — injected lucky rate vs measured luck rate.
3. **Dataset metrics** — luck rate, competent success rate, auditor
   accuracy, and uninformed rate by tool for a generated dataset.
4. **Risk-weighted luck** — per-mode risk scores (a guessed flight
   scores 0.75, a guessed hotel 0.25, though both are "lucky"),
   the aggregate Risk-Weighted Luck Score next to the plain Luck
   Rate, and the uninformed rate by risk tier.
