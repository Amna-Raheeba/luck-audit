"""Trace model: a recorded agent run as an ordered list of events.

A trace is the only input the auditor trusts. It carries no policy and
no judgement — just what happened, in order. Ground truth (which
arguments the generating agent had actually observed) is stored
separately under ``ground_truth`` and is NEVER read by the auditor; it
exists so experiments can measure the auditor's own accuracy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

EVENT_KINDS = ("user", "thought", "tool_call", "tool_result", "final")
OUTCOMES = ("success", "failure")


@dataclass
class TraceEvent:
    """One step of an agent run.

    kind: "user" | "thought" | "tool_call" | "tool_result" | "final".
    text: human-readable content (user message, reasoning, rendered
        result, final answer).
    data: structured payload. For tool_call: {"tool": name,
        "args": {...}, "call_id": str}. For tool_result: {"call_id":
        str, "result": {...}}. Other kinds leave it empty.
    """

    event_id: int
    kind: str
    text: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind,
            "text": self.text,
            "data": self.data,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "TraceEvent":
        return cls(
            event_id=int(raw["event_id"]),
            kind=str(raw["kind"]),
            text=str(raw.get("text", "")),
            data=dict(raw.get("data", {})),
        )


@dataclass
class Trace:
    """A complete agent run.

    run_id: stable identifier for the run.
    task: short description of what the agent was asked to do.
    outcome: "success" or "failure" — the run's own verdict, as the
        environment reported it. A "success" is exactly what the
        auditor is suspicious of.
    system_facts: constants the agent legitimately knows without
        observing them (e.g. today's date, its own agent id). Declared
        up front; anything not declared here is not evidence.
    ground_truth: optional per-call labels recorded by the trace
        generator: {call_id: {arg: "evidenced" | "uninformed"}}.
        The auditor never reads this.
    """

    run_id: str
    task: str
    outcome: str
    events: list[TraceEvent] = field(default_factory=list)
    system_facts: dict[str, Any] = field(default_factory=dict)
    ground_truth: dict[str, dict[str, str]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.outcome not in OUTCOMES:
            raise ValueError(f"outcome must be one of {OUTCOMES}, got {self.outcome!r}")
        for event in self.events:
            if event.kind not in EVENT_KINDS:
                raise ValueError(f"unknown event kind {event.kind!r}")
        ids = [e.event_id for e in self.events]
        if ids != sorted(ids) or len(set(ids)) != len(ids):
            raise ValueError("event_ids must be unique and in increasing order")

    def tool_calls(self) -> list[TraceEvent]:
        return [e for e in self.events if e.kind == "tool_call"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "task": self.task,
            "outcome": self.outcome,
            "system_facts": self.system_facts,
            "ground_truth": self.ground_truth,
            "events": [e.to_dict() for e in self.events],
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Trace":
        return cls(
            run_id=str(raw["run_id"]),
            task=str(raw.get("task", "")),
            outcome=str(raw["outcome"]),
            system_facts=dict(raw.get("system_facts", {})),
            ground_truth=dict(raw.get("ground_truth", {})),
            events=[TraceEvent.from_dict(e) for e in raw.get("events", [])],
        )

    def to_jsonl(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_jsonl(cls, line: str) -> "Trace":
        return cls.from_dict(json.loads(line))


def write_traces(traces: list[Trace], path: str | Path) -> None:
    """Write traces to a JSONL file, one trace per line."""
    with open(path, "w", encoding="utf-8") as fh:
        for trace in traces:
            fh.write(trace.to_jsonl() + "\n")


def read_traces(path: str | Path) -> list[Trace]:
    """Read traces from a JSONL file. Blank lines are skipped."""
    traces = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                traces.append(Trace.from_jsonl(line))
    return traces
