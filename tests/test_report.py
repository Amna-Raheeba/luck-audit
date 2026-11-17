"""Tests for report generation."""

import json

from luck_audit.audit import aggregate, audit_trace
from luck_audit.mock import demo_traces
from luck_audit.report import json_report, markdown_report


def _metrics_and_audits():
    traces = demo_traces()
    audits = [audit_trace(t) for t in traces]
    return aggregate(audits, traces), audits


def test_markdown_report_contains_headline_numbers():
    metrics, audits = _metrics_and_audits()
    text = markdown_report(metrics, audits)
    assert "Luck Rate: 75.0%" in text
    assert "Total runs: 5" in text
    assert "demo-lucky_flight" in text


def test_markdown_report_lists_uninformed_rates():
    metrics, audits = _metrics_and_audits()
    text = markdown_report(metrics, audits)
    assert "book_flight.seat" in text
    assert "Auditor accuracy" in text


def test_json_report_parses_and_matches():
    metrics, audits = _metrics_and_audits()
    data = json.loads(json_report(metrics, audits))
    assert data["metrics"]["luck_rate"] == 0.75
    assert len(data["runs"]) == 5
    assert data["runs"][0]["verdict"] == "competent"


def test_json_report_without_ground_truth_omits_section():
    from luck_audit.audit import aggregate as agg
    from luck_audit.mock import generate_trace

    traces = [generate_trace("r1", "competent", seed=1)]
    traces[0].ground_truth = {}
    audits = [audit_trace(t) for t in traces]
    metrics = agg(audits, traces)
    assert metrics.ground_truth_calls == 0
    assert "Auditor accuracy" not in markdown_report(metrics, audits)
