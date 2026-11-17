"""Tool schemas: which calls mutate the world, and what they must know.

The auditor is policy-free: it does not know whether booking a flight
is allowed, only whether the agent had the evidence to choose the
flight. The schema is the one place where the deployer declares the
facts of their own tools — which calls are mutating, and which of
their arguments are decision-critical (required).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Risk tiers for risk-weighted luck (see luck_audit/risk.py). A tier is
# a declared judgement about blast radius, not a measured quantity:
# "irreversible" means the call's effect cannot be undone without a
# second mutating call or a real-world cost (money moves, a seat is
# held, a record is deleted); "reversible" means it can be undone
# cleanly (a booking that cancels free of charge); "low" means the
# effect is trivially correctable. The weights below are the default
# policy — a deployer who disagrees declares their own.
RISK_TIERS = ("irreversible", "reversible", "low")

RISK_WEIGHTS: dict[str, float] = {
    "irreversible": 3.0,
    "reversible": 1.0,
    "low": 0.25,
}


def risk_weight(tier: str) -> float:
    """Weight of one risk tier. Unknown tiers raise, never default."""
    if tier not in RISK_WEIGHTS:
        raise ValueError(f"unknown risk tier {tier!r}; expected one of {RISK_TIERS}")
    return RISK_WEIGHTS[tier]


@dataclass(frozen=True)
class ToolSpec:
    """Specification of one tool.

    name: tool name as it appears in trace events.
    mutating: True if the call changes state outside the agent
        (booking, payment, deletion, sending). Read-only tools are
        never audited as mutating calls — but their results ARE
        evidence for later calls.
    required_args: decision-critical arguments. Each one must be
        traceable to an evidence span, or the call is uninformed.
        Arguments not listed here are ignored by the auditor (for
        example free-form notes).
    risk_tier: blast-radius tier of the call — "irreversible",
        "reversible", or "low" (see RISK_TIERS). Used only by the
        risk-weighted luck score; the plain luck rate ignores it.
        Defaults to "reversible" for mutating tools, "low" otherwise.
    """

    name: str
    mutating: bool
    required_args: tuple[str, ...] = ()
    risk_tier: str | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("ToolSpec needs a name")
        tier = self.risk_tier
        if tier is None:
            tier = "reversible" if self.mutating else "low"
            object.__setattr__(self, "risk_tier", tier)
        elif tier not in RISK_TIERS:
            raise ValueError(f"unknown risk tier {tier!r}; expected one of {RISK_TIERS}")


# The booking-domain schema used by the mock agent and the examples.
# A deployer audits their own tools by writing their own specs in
# exactly this shape — nothing about the auditor is booking-specific.
BOOKING_TOOLS: tuple[ToolSpec, ...] = (
    ToolSpec("search_flights", mutating=False),
    ToolSpec("get_flight_details", mutating=False),
    ToolSpec("search_hotels", mutating=False),
    # A flight booking is irreversible: the fare is charged at once and
    # is typically non-refundable, so a guessed flight is the worst
    # kind of lucky call. A hotel booking is reversible: it can be
    # cancelled free of charge inside its window, so a guessed hotel
    # is bad but recoverable. Cancelling destroys a reservation, so it
    # is irreversible too.
    ToolSpec(
        "book_flight",
        mutating=True,
        required_args=("flight_id", "passenger_name", "seat"),
        risk_tier="irreversible",
    ),
    ToolSpec(
        "book_hotel",
        mutating=True,
        required_args=("hotel_id", "check_in", "check_out", "guest_name"),
        risk_tier="reversible",
    ),
    ToolSpec(
        "cancel_booking",
        mutating=True,
        required_args=("booking_id",),
        risk_tier="irreversible",
    ),
)


def specs_by_name(specs: tuple[ToolSpec, ...] | list[ToolSpec]) -> dict[str, ToolSpec]:
    """Index tool specs by name. Duplicate names raise."""
    out: dict[str, ToolSpec] = {}
    for spec in specs:
        if spec.name in out:
            raise ValueError(f"duplicate tool spec: {spec.name}")
        out[spec.name] = spec
    return out
