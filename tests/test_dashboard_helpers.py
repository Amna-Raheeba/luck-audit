"""Tests for the dashboard helpers (pure functions, no Streamlit)."""

import pytest

from dashboard.helpers import (
    audit_demo,
    dataset_metrics,
    ledger_rows,
    risk_demo,
    sweep_summary,
)


def test_audit_demo_returns_five_runs():
    rows = audit_demo()
    assert len(rows) == 5
    verdicts = {row["run_id"]: row["verdict"] for row in rows}
    assert verdicts["demo-competent"] == "competent"
    assert verdicts["demo-lucky_flight"] == "lucky"
    assert verdicts["demo-wrong_flight"] == "failed"


def test_ledger_rows_show_uninformed_args():
    rows = ledger_rows("demo-lucky_seat")
    by_arg = {row["arg"]: row for row in rows if row["tool"] == "book_flight"}
    assert by_arg["seat"]["status"] == "uninformed"
    assert by_arg["flight_id"]["status"] == "evidenced"
    assert by_arg["flight_id"]["source"] == "tool_result"


def test_ledger_rows_unknown_run_rejected():
    with pytest.raises(ValueError):
        ledger_rows("demo-nope")


def test_sweep_summary_is_monotonic():
    rows = sweep_summary(n=50, seed=7)
    assert len(rows) == 5
    rates = [row["measured_luck_rate"] for row in rows]
    assert rates[0] == 0.0
    assert rates == sorted(rates)


def test_dataset_metrics_match_cli_numbers():
    metrics = dataset_metrics(n=200, lucky_rate=0.4, seed=7)
    assert metrics["total_runs"] == 200
    assert metrics["successful_runs"] == 175
    assert metrics["lucky_runs"] == 85
    assert metrics["luck_rate"] == pytest.approx(85 / 175)
    assert metrics["auditor_accuracy"] == 1.0


def test_risk_demo_separates_lucky_modes():
    rows = risk_demo()
    by_mode = {row["mode"]: row for row in rows}
    assert by_mode["competent"]["risk_score"] == 0.0
    assert by_mode["lucky_flight"]["risk_score"] == pytest.approx(0.75)
    assert by_mode["lucky_seat"]["risk_score"] == pytest.approx(0.75)
    assert by_mode["lucky_hotel"]["risk_score"] == pytest.approx(0.25)
    # All three lucky modes share the verdict "lucky" — the risk
    # score is what separates them.
    assert by_mode["lucky_flight"]["verdict"] == "lucky"
    assert by_mode["lucky_hotel"]["verdict"] == "lucky"


def test_dataset_metrics_include_risk_fields():
    metrics = dataset_metrics(n=200, lucky_rate=0.4, seed=7)
    assert metrics["risk_weighted_luck_score"] == pytest.approx(197 / 700)
    assert metrics["uninformed_rate_by_tier"]["irreversible"] == pytest.approx(0.32)
    assert metrics["risk_weight_by_tier"]["irreversible"] == pytest.approx(0.75)
