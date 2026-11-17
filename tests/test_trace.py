"""Tests for the trace model."""

import json

import pytest

from luck_audit.trace import Trace, TraceEvent, read_traces, write_traces


def _events():
    return [
        TraceEvent(1, "user", "Book a flight."),
        TraceEvent(2, "thought", "I will search."),
        TraceEvent(3, "final", "Done."),
    ]


def test_trace_constructs_and_reports_tool_calls():
    trace = Trace("r1", "book", "success", _events())
    assert trace.run_id == "r1"
    assert trace.tool_calls() == []


def test_bad_outcome_rejected():
    with pytest.raises(ValueError):
        Trace("r1", "book", "maybe", _events())


def test_bad_event_kind_rejected():
    with pytest.raises(ValueError):
        Trace("r1", "book", "success", [TraceEvent(1, "hallucination", "x")])


def test_duplicate_event_ids_rejected():
    events = [TraceEvent(1, "user", "a"), TraceEvent(1, "user", "b")]
    with pytest.raises(ValueError):
        Trace("r1", "book", "success", events)


def test_out_of_order_event_ids_rejected():
    events = [TraceEvent(2, "user", "a"), TraceEvent(1, "user", "b")]
    with pytest.raises(ValueError):
        Trace("r1", "book", "success", events)


def test_event_round_trip():
    event = TraceEvent(3, "tool_call", "call", {"tool": "book_flight", "args": {"seat": "14B"}})
    assert TraceEvent.from_dict(event.to_dict()) == event


def test_trace_round_trip(tmp_path):
    trace = Trace("r1", "book", "success", _events(), system_facts={"today": "2026-12-05"})
    path = tmp_path / "t.jsonl"
    write_traces([trace], path)
    loaded = read_traces(path)
    assert len(loaded) == 1
    assert loaded[0].to_dict() == trace.to_dict()


def test_read_traces_skips_blank_lines(tmp_path):
    path = tmp_path / "t.jsonl"
    trace = Trace("r1", "book", "success", _events())
    path.write_text("\n" + trace.to_jsonl() + "\n\n", encoding="utf-8")
    assert len(read_traces(path)) == 1


def test_jsonl_line_is_valid_json():
    trace = Trace("r1", "book", "success", _events())
    assert json.loads(trace.to_jsonl())["run_id"] == "r1"


def test_tool_call_event_carries_call_id():
    event = TraceEvent(1, "tool_call", "", {"tool": "book_flight", "call_id": "call-1"})
    trace = Trace("r1", "book", "success", [event])
    assert trace.tool_calls()[0].data["call_id"] == "call-1"
