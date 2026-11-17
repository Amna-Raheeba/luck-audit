"""Tests for run verdicts and aggregate metrics."""

from luck_audit.audit import aggregate, audit_trace
from luck_audit.mock import demo_traces, generate_dataset, generate_trace


def test_competent_verdict():
    audit = audit_trace(generate_trace("r1", "competent", seed=1))
    assert audit.verdict == "competent"
    assert audit.outcome == "success"
    assert not audit.is_lucky
    assert audit.evidence_coverage == 1.0


def test_lucky_verdicts():
    for mode in ("lucky_flight", "lucky_seat", "lucky_hotel"):
        audit = audit_trace(generate_trace("r1", mode, seed=1))
        assert audit.verdict == "lucky", mode
        assert audit.is_lucky
        assert audit.lucky_calls >= 1


def test_failed_verdict_is_not_lucky():
    audit = audit_trace(generate_trace("r1", "wrong_flight", seed=1))
    assert audit.verdict == "failed"
    assert audit.outcome == "failure"
    assert not audit.is_lucky


def test_demo_set_luck_rate():
    traces = demo_traces()
    audits = [audit_trace(t) for t in traces]
    metrics = aggregate(audits, traces)
    assert metrics.total_runs == 5
    assert metrics.successful_runs == 4
    assert metrics.lucky_runs == 3
    assert metrics.luck_rate == 0.75
    assert metrics.competent_success_rate == 0.2


def test_luck_rate_none_without_successes():
    traces = [generate_trace("r1", "wrong_flight", seed=1)]
    audits = [audit_trace(t) for t in traces]
    metrics = aggregate(audits, traces)
    assert metrics.luck_rate is None
    assert metrics.successful_runs == 0


def test_uninformed_rates_by_tool_and_arg():
    traces = demo_traces()
    audits = [audit_trace(t) for t in traces]
    metrics = aggregate(audits, traces)
    assert metrics.uninformed_rate_by_tool["book_flight"] > 0
    assert metrics.uninformed_rate_by_tool["book_hotel"] > 0
    assert metrics.uninformed_rate_by_arg["book_flight.seat"] > 0
    assert metrics.uninformed_rate_by_arg["book_flight.passenger_name"] == 0.0


def test_aggregate_counts_mutating_calls():
    traces = demo_traces()
    audits = [audit_trace(t) for t in traces]
    metrics = aggregate(audits, traces)
    assert metrics.total_mutating_calls == 9
    assert metrics.lucky_calls == 4


def test_auditor_accuracy_on_large_dataset():
    traces = generate_dataset(n=200, lucky_rate=0.4, wrong_rate=0.1, seed=7)
    audits = [audit_trace(t) for t in traces]
    metrics = aggregate(audits, traces)
    assert metrics.ground_truth_calls > 1000
    assert metrics.auditor_precision == 1.0
    assert metrics.auditor_recall == 1.0
    assert metrics.auditor_accuracy == 1.0


def test_luck_rate_grows_with_injected_luck():
    rates = []
    for lucky in (0.0, 0.4, 0.8):
        traces = generate_dataset(n=100, lucky_rate=lucky, wrong_rate=0.1, seed=3)
        metrics = aggregate([audit_trace(t) for t in traces], traces)
        rates.append(metrics.luck_rate)
    assert rates[0] == 0.0
    assert rates[0] < rates[1] < rates[2]


def test_run_audit_to_dict_is_json_safe():
    import json

    audit = audit_trace(generate_trace("r1", "lucky_seat", seed=1))
    json.dumps(audit.to_dict())
