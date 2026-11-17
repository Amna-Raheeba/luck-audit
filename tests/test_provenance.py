"""Tests for the provenance ledger — the heart of the audit."""

import pytest

from luck_audit.provenance import EvidenceLedger
from luck_audit.schema import BOOKING_TOOLS, ToolSpec
from luck_audit.trace import Trace, TraceEvent


def _trace(events, system_facts=None):
    return Trace("r1", "book", "success", events, system_facts=system_facts or {})


def _call(event_id, tool, args, call_id="call-1"):
    return TraceEvent(
        event_id, "tool_call", f"Call {tool}", {"tool": tool, "args": args, "call_id": call_id}
    )


def _result(event_id, result, call_id="call-0"):
    return TraceEvent(
        event_id, "tool_result", f"Result: {result}", {"call_id": call_id, "result": result}
    )


def _ledger_for(trace):
    return EvidenceLedger(BOOKING_TOOLS).build(trace)


def test_user_message_is_evidence():
    trace = _trace([
        TraceEvent(1, "user", "Book a flight for Amna Raheeba."),
        _call(2, "book_flight", {"flight_id": "PK-301", "passenger_name": "Amna Raheeba", "seat": "14B"}),
    ])
    ledger = _ledger_for(trace)[0]
    by_arg = {e.arg: e for e in ledger.entries}
    assert by_arg["passenger_name"].status == "evidenced"
    assert by_arg["passenger_name"].source_kind == "user"
    assert by_arg["flight_id"].status == "uninformed"


def test_tool_result_field_is_evidence():
    trace = _trace([
        TraceEvent(1, "user", "Find a flight."),
        _result(2, {"flights": [{"flight_id": "PK-301"}]}, call_id="call-0"),
        _call(3, "book_flight", {"flight_id": "PK-301", "passenger_name": "Amna Raheeba", "seat": "14B"}),
    ])
    ledger = _ledger_for(trace)[0]
    entry = next(e for e in ledger.entries if e.arg == "flight_id")
    assert entry.status == "evidenced"
    assert entry.source_kind == "tool_result"
    assert entry.source_field == "flights[0].flight_id"


def test_thought_is_never_evidence():
    trace = _trace([
        TraceEvent(1, "user", "Book a flight."),
        TraceEvent(2, "thought", "The flight must be PK-301, I am sure of it."),
        _call(3, "book_flight", {"flight_id": "PK-301", "passenger_name": "Amna Raheeba", "seat": "14B"}),
    ])
    ledger = _ledger_for(trace)[0]
    entry = next(e for e in ledger.entries if e.arg == "flight_id")
    assert entry.status == "uninformed"
    assert entry.source_kind is None


def test_final_answer_is_never_evidence():
    trace = _trace([
        _call(1, "book_flight", {"flight_id": "PK-301", "passenger_name": "Amna Raheeba", "seat": "14B"}),
        TraceEvent(2, "final", "Booked PK-301, seat 14B."),
    ])
    ledger = _ledger_for(trace)[0]
    assert all(e.status == "uninformed" for e in ledger.entries)


def test_earliest_evidence_wins():
    trace = _trace([
        TraceEvent(1, "user", "Book flight PK-301."),
        _result(2, {"flight_id": "PK-301"}, call_id="call-0"),
        _call(3, "book_flight", {"flight_id": "PK-301", "passenger_name": "Amna Raheeba", "seat": "14B"}),
    ])
    ledger = _ledger_for(trace)[0]
    entry = next(e for e in ledger.entries if e.arg == "flight_id")
    assert entry.source_kind == "user"
    assert entry.source_event_id == 1


def test_system_fact_is_evidence():
    trace = _trace(
        [_call(1, "book_hotel", {"hotel_id": "HT-101", "check_in": "2026-12-05", "check_out": "2026-12-07", "guest_name": "Amna Raheeba"})],
        system_facts={"today": "2026-12-05"},
    )
    ledger = _ledger_for(trace)[0]
    entry = next(e for e in ledger.entries if e.arg == "check_in")
    assert entry.status == "evidenced"
    assert entry.source_kind == "system"
    assert entry.source_field == "today"


def test_chained_argument_is_evidence():
    trace = _trace([
        _result(1, {"booking_id": "BK-PK-301-001"}, call_id="call-0"),
        _call(2, "book_flight", {"flight_id": "PK-301", "passenger_name": "Amna Raheeba", "seat": "14B"}, call_id="call-1"),
        _call(3, "cancel_booking", {"booking_id": "BK-PK-301-001"}, call_id="call-2"),
    ])
    ledgers = _ledger_for(trace)
    cancel = next(ledger for ledger in ledgers if ledger.tool == "cancel_booking")
    entry = cancel.entries[0]
    # booking_id came from the book_flight result via the earlier call.
    assert entry.status == "evidenced"
    assert entry.source_kind in ("tool_result", "chained")


def test_chained_through_uninformed_arg_does_not_count():
    trace = _trace([
        TraceEvent(1, "user", "Book something."),
        _call(2, "book_flight", {"flight_id": "PK-301", "passenger_name": "Amna Raheeba", "seat": "14B"}, call_id="call-1"),
        _call(3, "cancel_booking", {"booking_id": "BK-PK-301-001"}, call_id="call-2"),
    ])
    ledgers = _ledger_for(trace)
    cancel = next(ledger for ledger in ledgers if ledger.tool == "cancel_booking")
    assert cancel.entries[0].status == "uninformed"


def test_missing_argument_is_uninformed():
    trace = _trace([
        TraceEvent(1, "user", "Book a flight."),
        _call(2, "book_flight", {"flight_id": "PK-301", "passenger_name": "Amna Raheeba"}),
    ])
    ledger = _ledger_for(trace)[0]
    entry = next(e for e in ledger.entries if e.arg == "seat")
    assert entry.status == "uninformed"
    assert entry.value is None


def test_non_mutating_calls_are_not_audited():
    trace = _trace([
        _call(1, "search_flights", {"origin": "Lahore", "destination": "Karachi", "date": "2026-12-05"}),
    ])
    assert _ledger_for(trace) == []


def test_unknown_tool_is_skipped():
    trace = _trace([
        _call(1, "teleport", {"destination": "Karachi"}),
    ])
    assert _ledger_for(trace) == []


def test_ledger_flags_lucky_call_and_coverage():
    trace = _trace([
        TraceEvent(1, "user", "Book a flight for Amna Raheeba."),
        _call(2, "book_flight", {"flight_id": "PK-301", "passenger_name": "Amna Raheeba", "seat": "14B"}),
    ])
    ledger = _ledger_for(trace)[0]
    assert ledger.is_lucky
    assert ledger.uninformed_args == ["flight_id", "seat"]
    assert ledger.evidence_coverage == pytest.approx(1 / 3)
