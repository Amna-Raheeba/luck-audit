"""Tests for risk-weighted luck (luck_audit/risk.py)."""

import json

import pytest

from luck_audit import aggregate, audit_trace
from luck_audit.mock import demo_traces, generate_dataset, generate_trace
from luck_audit.report import json_report, markdown_report
from luck_audit.risk import aggregate_risk, pearson, run_risk_score
from luck_audit.schema import BOOKING_TOOLS, ToolSpec, risk_weight
from luck_audit.trace import Trace, TraceEvent


def test_risk_weight_mapping():
    assert risk_weight("irreversible") == 3.0
    assert risk_weight("reversible") == 1.0
    assert risk_weight("low") == 0.25
    with pytest.raises(ValueError):
        risk_weight("catastrophic")


def test_tool_spec_default_tiers():
    assert ToolSpec("pay", mutating=True).risk_tier == "reversible"
    assert ToolSpec("read", mutating=False).risk_tier == "low"
    assert ToolSpec("pay", mutating=True, risk_tier="irreversible").risk_tier == "irreversible"
    with pytest.raises(ValueError):
        ToolSpec("pay", mutating=True, risk_tier="nuclear")


def test_booking_tool_tiers():
    by_name = {s.name: s for s in BOOKING_TOOLS}
    assert by_name["book_flight"].risk_tier == "irreversible"
    assert by_name["book_hotel"].risk_tier == "reversible"
    assert by_name["cancel_booking"].risk_tier == "irreversible"
    assert by_name["search_flights"].risk_tier == "low"


def test_demo_modes_separate_by_risk():
    # The plain verdict calls all three lucky modes "lucky". The risk
    # score separates the irreversible guess (flight) from the
    # reversible one (hotel): 0.75 vs 0.25.
    audits = {t.run_id: audit_trace(t) for t in demo_traces()}
    assert audits["demo-competent"].risk_score == 0.0
    assert audits["demo-lucky_flight"].risk_score == pytest.approx(0.75)
    assert audits["demo-lucky_seat"].risk_score == pytest.approx(0.75)
    assert audits["demo-lucky_hotel"].risk_score == pytest.approx(0.25)
    # A failed run still gets a per-run score (its one irreversible
    # call was lucky); the aggregate excludes failed runs.
    assert audits["demo-wrong_flight"].risk_score == pytest.approx(1.0)


def test_run_risk_score_none_without_mutating_calls():
    trace = Trace(
        run_id="empty",
        task="nothing",
        outcome="success",
        events=[TraceEvent(event_id=1, kind="user", text="hello")],
    )
    assert audit_trace(trace).risk_score is None
    assert run_risk_score([]) is None


def test_aggregate_risk_on_headline_dataset():
    traces = generate_dataset(n=200, lucky_rate=0.4, wrong_rate=0.1, seed=7)
    metrics = aggregate([audit_trace(t) for t in traces], traces)
    # Plain luck rate is unchanged by the feature.
    assert metrics.luck_rate == pytest.approx(85 / 175)
    # 56 lucky irreversible calls (weight 3) + 29 lucky reversible
    # calls (weight 1) over 175 successful runs x (3 + 1) weight.
    assert metrics.risk_weighted_luck_score == pytest.approx(197 / 700)
    assert metrics.lucky_weight == pytest.approx(197.0)
    assert metrics.total_weight == pytest.approx(700.0)
    assert metrics.uninformed_rate_by_tier["irreversible"] == pytest.approx(0.32)
    assert metrics.uninformed_rate_by_tier["reversible"] == pytest.approx(29 / 175)
    # Irreversible calls carry 75% of the total risk weight.
    assert metrics.risk_weight_by_tier["irreversible"] == pytest.approx(0.75)


def test_aggregate_risk_uses_deployer_tiers():
    # If a deployer declares hotel bookings irreversible too, the
    # weighted score becomes the plain uninformed-call rate over
    # successful runs — the weighting mechanics, not the default
    # policy, are what the test pins down.
    traces = generate_dataset(n=200, lucky_rate=0.4, wrong_rate=0.1, seed=7)
    audits = [audit_trace(t) for t in traces]
    flat_specs = tuple(
        ToolSpec(s.name, s.mutating, s.required_args, risk_tier="irreversible")
        if s.mutating
        else s
        for s in BOOKING_TOOLS
    )
    risk = aggregate_risk(audits, flat_specs)
    assert risk["risk_weighted_luck_score"] == pytest.approx(85 / 350)
    assert risk["uninformed_rate_by_tier"] == {"irreversible": pytest.approx(85 / 350)}


def test_aggregate_risk_none_without_successful_mutating_calls():
    traces = [generate_trace("f-1", "wrong_flight", seed=1)]
    metrics = aggregate([audit_trace(t) for t in traces], traces)
    assert metrics.risk_weighted_luck_score is None
    assert metrics.luck_rate is None


def test_pearson():
    assert pearson([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)
    assert pearson([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0)
    assert pearson([1, 1, 1], [1, 2, 3]) is None  # no variance
    assert pearson([1], [1]) is None  # too few points
    assert pearson([1, 2], [1, 2, 3]) is None  # mismatched lengths


def test_risk_score_survives_serialisation():
    traces = generate_dataset(n=20, lucky_rate=0.4, wrong_rate=0.1, seed=7)
    audits = [audit_trace(t) for t in traces]
    metrics = aggregate(audits, traces)
    data = json.loads(json_report(metrics, audits))
    assert data["metrics"]["risk_weighted_luck_score"] is not None
    assert all("risk_score" in run for run in data["runs"])


def test_markdown_report_has_risk_section():
    traces = generate_dataset(n=20, lucky_rate=0.4, wrong_rate=0.1, seed=7)
    audits = [audit_trace(t) for t in traces]
    metrics = aggregate(audits, traces)
    report = markdown_report(metrics, audits)
    assert "Risk-Weighted Luck Score" in report
    assert "Uninformed rate by risk tier" in report
    assert "irreversible" in report
