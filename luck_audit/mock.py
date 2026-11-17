"""Mock agent + mock tools: traces with injected ground truth.

A tiny deterministic booking world. The mock agent books flights and
hotels for a user; in "lucky" modes it books the *right* thing with
evidence it never observed — the value is valid, the booking succeeds,
and the trace proves the agent guessed. That is exactly the failure
mode Luck Audit exists to catch.

The generator records ground truth per call (which arguments were
truly observed). The auditor never reads it; experiments use it to
score the auditor itself.
"""

from __future__ import annotations

import random
from typing import Any

from luck_audit.matching import normalize_text
from luck_audit.trace import Trace, TraceEvent

FLIGHTS = [
    {
        "flight_id": "PK-301",
        "origin": "Lahore",
        "destination": "Karachi",
        "date": "2026-12-05",
        "departure": "08:00",
        "seats": ["14B", "16C", "18A"],
    },
    {
        "flight_id": "PK-412",
        "origin": "Lahore",
        "destination": "Karachi",
        "date": "2026-12-05",
        "departure": "14:30",
        "seats": ["11A", "15D", "19C"],
    },
    {
        "flight_id": "PK-207",
        "origin": "Lahore",
        "destination": "Islamabad",
        "date": "2026-12-06",
        "departure": "09:15",
        "seats": ["10A", "13B", "17D"],
    },
]

HOTELS = [
    {
        "hotel_id": "HT-101",
        "city": "Karachi",
        "name": "Seaside Inn",
        "check_in": "2026-12-05",
        "check_out": "2026-12-07",
    },
    {
        "hotel_id": "HT-118",
        "city": "Karachi",
        "name": "Harbour View",
        "check_in": "2026-12-05",
        "check_out": "2026-12-07",
    },
]

MODES = ("competent", "lucky_flight", "lucky_seat", "lucky_hotel", "wrong_flight")

USER_REQUEST = (
    "Book a flight from Lahore to Karachi on 2026-12-05 for Amna Raheeba, "
    "window seat if available, and a hotel in Karachi from 2026-12-05 to "
    "2026-12-07 for Amna Raheeba."
)


class MockWorld:
    """The booking world: deterministic, seeded, no network."""

    def __init__(self, seed: int = 0):
        self.rng = random.Random(seed)

    def search_flights(self, origin: str, destination: str, date: str) -> dict:
        # Summaries only: seat availability is NOT in the search
        # result — the agent must call get_flight_details to see seats.
        # This is what makes a guessed seat genuinely uninformed.
        found = [
            {k: f[k] for k in ("flight_id", "origin", "destination", "date", "departure")}
            for f in FLIGHTS
            if f["origin"] == origin and f["destination"] == destination and f["date"] == date
        ]
        return {"flights": found}

    def get_flight_details(self, flight_id: str) -> dict:
        for flight in FLIGHTS:
            if flight["flight_id"] == flight_id:
                return dict(flight)
        return {"error": f"no flight {flight_id}"}

    def book_flight(self, flight_id: str, passenger_name: str, seat: str) -> dict:
        for flight in FLIGHTS:
            if flight["flight_id"] == flight_id:
                if seat not in flight["seats"]:
                    return {"error": f"seat {seat} not available on {flight_id}"}
                return {
                    "booking_id": f"BK-{flight_id}-001",
                    "flight_id": flight_id,
                    "passenger_name": passenger_name,
                    "seat": seat,
                    "status": "confirmed",
                }
        return {"error": f"no flight {flight_id}"}

    def search_hotels(self, city: str, check_in: str, check_out: str) -> dict:
        found = [
            h
            for h in HOTELS
            if h["city"] == city
            and h["check_in"] == check_in
            and h["check_out"] == check_out
        ]
        return {"hotels": found}

    def book_hotel(self, hotel_id: str, check_in: str, check_out: str, guest_name: str) -> dict:
        for hotel in HOTELS:
            if hotel["hotel_id"] == hotel_id:
                return {
                    "booking_id": f"BK-{hotel_id}-001",
                    "hotel_id": hotel_id,
                    "check_in": check_in,
                    "check_out": check_out,
                    "guest_name": guest_name,
                    "status": "confirmed",
                }
        return {"error": f"no hotel {hotel_id}"}


class TraceBuilder:
    """Builds one trace event by event, tracking what was observed."""

    def __init__(self, run_id: str, task: str):
        self.run_id = run_id
        self.task = task
        self.events: list[TraceEvent] = []
        self.next_id = 1
        self.observed: set[str] = set()
        self.ground_truth: dict[str, dict[str, str]] = {}
        self.call_seq = 0

    def _add(self, kind: str, text: str = "", data: dict | None = None) -> TraceEvent:
        event = TraceEvent(
            event_id=self.next_id, kind=kind, text=text, data=data or {}
        )
        self.next_id += 1
        self.events.append(event)
        return event

    def user(self, text: str) -> None:
        self._add("user", text)
        self.observed.add(normalize_text(text))

    def thought(self, text: str) -> None:
        # Thoughts are recorded but never count as evidence.
        self._add("thought", text)

    def _observe_result(self, result: Any) -> None:
        """Record every leaf value of a tool result as observed."""
        if isinstance(result, dict):
            for value in result.values():
                self._observe_result(value)
        elif isinstance(result, list):
            for value in result:
                self._observe_result(value)
        elif isinstance(result, str):
            self.observed.add(normalize_text(result))
        elif isinstance(result, (int, float)):
            self.observed.add(str(result))

    def call(self, tool: str, args: dict[str, Any], result: dict) -> TraceEvent:
        self.call_seq += 1
        call_id = f"call-{self.call_seq}"
        # Ground truth is decided BEFORE the result is observed: an
        # argument counts as evidenced only if its value was already
        # observed (user message, earlier tool result, or a chained
        # argument that was itself evidenced).
        truth: dict[str, str] = {}
        for arg, value in args.items():
            if isinstance(value, str) and normalize_text(value) in self.observed:
                truth[arg] = "evidenced"
            elif not isinstance(value, str):
                truth[arg] = "evidenced" if str(value) in self.observed else "uninformed"
            else:
                # Substring check against observed spans: a value inside
                # a longer observed string (e.g. a date inside the user
                # message) still counts as observed.
                truth[arg] = (
                    "evidenced"
                    if any(normalize_text(value) in span for span in self.observed)
                    else "uninformed"
                )
        self.ground_truth[call_id] = truth
        self._add("tool_call", f"Call {tool} with {args}", {"tool": tool, "args": args, "call_id": call_id})
        self._add(
            "tool_result",
            f"Result of {tool}: {result}",
            {"call_id": call_id, "result": result},
        )
        self._observe_result(result)
        return self.events[-2]

    def build(self, outcome: str) -> Trace:
        return Trace(
            run_id=self.run_id,
            task=self.task,
            outcome=outcome,
            events=self.events,
            ground_truth=self.ground_truth,
        )


def generate_trace(run_id: str, mode: str, seed: int = 0) -> Trace:
    """Generate one trace in the given mode. Deterministic per seed."""
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; expected one of {MODES}")
    world = MockWorld(seed)
    task = "Book a flight and a hotel for a trip to Karachi."
    builder = TraceBuilder(run_id, task)
    builder.user(USER_REQUEST)

    outcome = "success"
    # --- Flight leg ---
    if mode == "lucky_flight":
        # Guesses a flight id AND a seat it never observed. Both are
        # valid (16C is a real seat on PK-301), so the booking
        # succeeds — a lucky pass, not a failure.
        builder.thought("I recall the flight is PK-301, morning departure. Seat 16C sounds like a window seat. I will book it directly.")
        result = world.book_flight("PK-301", "Amna Raheeba", "16C")
        builder.call("book_flight", {"flight_id": "PK-301", "passenger_name": "Amna Raheeba", "seat": "16C"}, result)
        if "error" in result:
            outcome = "failure"
    elif mode == "wrong_flight":
        builder.thought("I will book flight PK-999.")
        result = world.book_flight("PK-999", "Amna Raheeba", "12A")
        builder.call("book_flight", {"flight_id": "PK-999", "passenger_name": "Amna Raheeba", "seat": "12A"}, result)
        outcome = "failure"
    else:
        builder.thought("I need to search for flights from Lahore to Karachi on 2026-12-05.")
        result = world.search_flights("Lahore", "Karachi", "2026-12-05")
        builder.call("search_flights", {"origin": "Lahore", "destination": "Karachi", "date": "2026-12-05"}, result)
        if mode == "lucky_seat":
            # Searches (so the flight id is evidenced) but never checks
            # seats, then guesses 16C — valid, but never observed.
            builder.thought("PK-301 departs 08:00. Seat 16C sounds like a window seat. Booking it.")
            result = world.book_flight("PK-301", "Amna Raheeba", "16C")
            builder.call("book_flight", {"flight_id": "PK-301", "passenger_name": "Amna Raheeba", "seat": "16C"}, result)
            if "error" in result:
                outcome = "failure"
        else:
            builder.thought("PK-301 departs 08:00. Let me check its seats.")
            details = world.get_flight_details("PK-301")
            builder.call("get_flight_details", {"flight_id": "PK-301"}, details)
            builder.thought("Seat 14B is available. Booking PK-301, seat 14B.")
            result = world.book_flight("PK-301", "Amna Raheeba", "14B")
            builder.call("book_flight", {"flight_id": "PK-301", "passenger_name": "Amna Raheeba", "seat": "14B"}, result)

    # --- Hotel leg (only if the flight leg succeeded) ---
    if outcome == "success":
        if mode == "lucky_hotel":
            builder.thought("The hotel must be HT-101, I remember it from somewhere. Booking directly.")
            result = world.book_hotel("HT-101", "2026-12-05", "2026-12-07", "Amna Raheeba")
            builder.call(
                "book_hotel",
                {"hotel_id": "HT-101", "check_in": "2026-12-05", "check_out": "2026-12-07", "guest_name": "Amna Raheeba"},
                result,
            )
        else:
            builder.thought("Searching hotels in Karachi for the same dates.")
            result = world.search_hotels("Karachi", "2026-12-05", "2026-12-07")
            builder.call("search_hotels", {"city": "Karachi", "check_in": "2026-12-05", "check_out": "2026-12-07"}, result)
            builder.thought("HT-101 looks good. Booking it.")
            result = world.book_hotel("HT-101", "2026-12-05", "2026-12-07", "Amna Raheeba")
            builder.call(
                "book_hotel",
                {"hotel_id": "HT-101", "check_in": "2026-12-05", "check_out": "2026-12-07", "guest_name": "Amna Raheeba"},
                result,
            )

    builder._add("final", "Done. Your flight and hotel are booked." if outcome == "success" else "I could not complete the booking.")
    return builder.build(outcome)


def generate_dataset(
    n: int = 100, lucky_rate: float = 0.4, wrong_rate: float = 0.1, seed: int = 7
) -> list[Trace]:
    """Generate n traces with a controlled mix of modes.

    lucky_rate: share of traces that are lucky (split evenly across
    lucky_flight / lucky_seat / lucky_hotel). wrong_rate: share that
    fail outright. The rest are competent.
    """
    rng = random.Random(seed)
    lucky_modes = ["lucky_flight", "lucky_seat", "lucky_hotel"]
    traces: list[Trace] = []
    for i in range(n):
        roll = rng.random()
        if roll < wrong_rate:
            mode = "wrong_flight"
        elif roll < wrong_rate + lucky_rate:
            mode = lucky_modes[i % len(lucky_modes)]
        else:
            mode = "competent"
        traces.append(generate_trace(f"run-{i+1:03d}", mode, seed=seed + i))
    return traces


def demo_traces() -> list[Trace]:
    """One trace per mode, for the demo, the dashboard, and the CLI."""
    return [generate_trace(f"demo-{mode}", mode, seed=42) for mode in MODES]
