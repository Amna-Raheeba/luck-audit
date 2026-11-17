"""Luck Audit dashboard: audit demo traces and inspect the ledgers.

Runs the real pipeline (mock traces -> EvidenceLedger -> aggregate),
never a second implementation of it.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import streamlit as st

from dashboard.helpers import (
    audit_demo,
    dataset_metrics,
    ledger_rows,
    risk_demo,
    sweep_summary,
)

st.set_page_config(page_title="Luck Audit", layout="wide")
st.title("Luck Audit")
st.write(
    "A successful agent run is not trustworthy if a mutating tool call "
    "was made without the evidence to choose it correctly. This dashboard "
    "audits recorded traces and reports the share of passes that were "
    "lucky, not competent."
)

tab_demo, tab_sweep, tab_dataset, tab_risk = st.tabs(
    ["Demo traces", "Luck-rate sweep", "Dataset metrics", "Risk-weighted luck"]
)

with tab_demo:
    st.header("Demo traces")
    if st.button("Run audit on demo traces"):
        rows = audit_demo()
        st.dataframe(rows, width="stretch")
        lucky = sum(1 for r in rows if r["verdict"] == "lucky")
        successful = sum(1 for r in rows if r["outcome"] == "success")
        st.metric("Luck rate (demo)", f"{lucky}/{successful} successful runs lucky")
        run_id = st.selectbox("Inspect a run's ledger", [r["run_id"] for r in rows])
        st.dataframe(ledger_rows(run_id), width="stretch")
    else:
        st.write("Press the button to audit one trace per agent mode.")

with tab_sweep:
    st.header("Luck-rate sweep")
    st.write(
        "Injected lucky rate vs measured luck rate (n=100 per point, "
        "10% of traces fail outright). The measured rate is a share of "
        "successful runs, so it runs above the injected share."
    )
    rows = sweep_summary(n=100, seed=7)
    st.bar_chart(rows, x="injected_lucky_rate", y="measured_luck_rate")
    st.dataframe(rows, width="stretch")

with tab_dataset:
    st.header("Dataset metrics")
    n = st.slider("Traces", 20, 500, 200, step=20)
    lucky_rate = st.slider("Injected lucky rate", 0.0, 0.8, 0.4, step=0.1)
    metrics = dataset_metrics(n=n, lucky_rate=lucky_rate, seed=7)
    col1, col2, col3 = st.columns(3)
    col1.metric("Luck rate", f"{metrics['luck_rate']:.1%}" if metrics["luck_rate"] is not None else "n/a")
    col2.metric("Competent success rate", f"{metrics['competent_success_rate']:.1%}")
    col3.metric("Auditor accuracy", f"{metrics['auditor_accuracy']:.1%}")
    st.write("Uninformed rate by tool")
    st.dataframe(
        [{"tool": k, "uninformed_rate": round(v, 3)} for k, v in metrics["uninformed_rate_by_tool"].items()],
        width="stretch",
    )

with tab_risk:
    st.header("Risk-weighted luck")
    st.write(
        "The plain Luck Rate counts a guessed flight and a guessed "
        "hotel the same way — one lucky run each. But a flight booking "
        "charges a non-refundable fare the moment it is made, while a "
        "hotel booking can usually be cancelled free of charge. The "
        "Risk-Weighted Luck Score prices each lucky call by its blast "
        "radius (irreversible ×3.0, reversible ×1.0, low ×0.25 — a "
        "declared policy, see docs/metrics.md §7)."
    )
    rows = risk_demo()
    st.bar_chart(rows, x="mode", y="risk_score")
    st.dataframe(rows, width="stretch")
    metrics = dataset_metrics(n=200, lucky_rate=0.4, seed=7)
    col1, col2 = st.columns(2)
    col1.metric("Luck rate (n=200)", f"{metrics['luck_rate']:.1%}")
    rwls = metrics["risk_weighted_luck_score"]
    col2.metric(
        "Risk-Weighted Luck Score (n=200)",
        f"{rwls:.1%}" if rwls is not None else "n/a",
    )
    st.write("Uninformed rate by risk tier")
    st.dataframe(
        [
            {
                "tier": tier,
                "uninformed_rate": round(rate, 3),
                "share_of_risk_weight": round(
                    metrics["risk_weight_by_tier"].get(tier, 0.0), 3
                ),
            }
            for tier, rate in metrics["uninformed_rate_by_tier"].items()
        ],
        width="stretch",
    )
