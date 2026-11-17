"""Tests for the mock agent and world."""

from luck_audit.mock import (
    MODES,
    MockWorld,
    demo_traces,
    generate_dataset,
    generate_trace,
)


def test_all_modes_generate():
    for mode in MODES:
        trace = generate_trace("r1", mode, seed=5)
        assert trace.run_id == "r1"
        assert trace.events


def test_unknown_mode_rejected():
    import pytest

    with pytest.raises(ValueError):
        generate_trace("r1", "teleport", seed=5)


def test_generation_is_deterministic():
    a = generate_trace("r1", "lucky_hotel", seed=11)
    b = generate_trace("r1", "lucky_hotel", seed=11)
    assert a.to_dict() == b.to_dict()


def test_competent_trace_has_full_ground_truth_evidenced():
    trace = generate_trace("r1", "competent", seed=5)
    for call_id, args in trace.ground_truth.items():
        assert all(label == "evidenced" for label in args.values()), call_id


def _truth_for_tool(trace, tool):
    call_ids = [
        e.data["call_id"] for e in trace.events
        if e.kind == "tool_call" and e.data.get("tool") == tool
    ]
    assert len(call_ids) == 1, f"expected one {tool} call, got {call_ids}"
    return trace.ground_truth[call_ids[0]]


def test_lucky_flight_ground_truth_marks_flight_and_seat():
    trace = generate_trace("r1", "lucky_flight", seed=5)
    truth = _truth_for_tool(trace, "book_flight")
    assert truth["flight_id"] == "uninformed"
    assert truth["seat"] == "uninformed"
    assert truth["passenger_name"] == "evidenced"


def test_lucky_seat_ground_truth_marks_only_seat():
    trace = generate_trace("r1", "lucky_seat", seed=5)
    truth = _truth_for_tool(trace, "book_flight")
    assert truth["flight_id"] == "evidenced"
    assert truth["seat"] == "uninformed"


def test_world_booking_rejects_unknown_flight():
    world = MockWorld(seed=1)
    result = world.book_flight("PK-999", "Amna Raheeba", "14B")
    assert "error" in result


def test_world_booking_rejects_unavailable_seat():
    world = MockWorld(seed=1)
    result = world.book_flight("PK-301", "Amna Raheeba", "99Z")
    assert "error" in result


def test_dataset_mix_matches_rates_roughly():
    traces = generate_dataset(n=200, lucky_rate=0.4, wrong_rate=0.1, seed=7)
    outcomes = [t.outcome for t in traces]
    assert outcomes.count("failure") == 25  # wrong_rate 0.1, seeded
    assert outcomes.count("success") == 175


def test_demo_traces_cover_all_modes():
    traces = demo_traces()
    assert len(traces) == len(MODES)
    assert [t.run_id for t in traces] == [f"demo-{mode}" for mode in MODES]
