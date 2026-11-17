"""Evidence-sufficiency provenance ledger.

For each mutating call, every required argument is traced to the
earliest trace span that supplied it — or marked ``uninformed``.

What counts as evidence (in search order, earliest span first):
  - "user": the value appears in a user message.
  - "system": the value equals a declared system fact.
  - "tool_result": the value appears in a tool result — as an exact
    structured field, or inside the result text.
  - "chained": the value equals an argument of an earlier tool call
    whose own argument was itself evidenced (provenance is transitive
    only through evidenced arguments).

What never counts: the agent's own reasoning ("thought") and its final
answer. A value the model merely thought about is not evidence — that
is the whole point of the audit. A value that first appears in the very
call being audited is not evidence either.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from luck_audit.matching import find_in_structured, value_in_text, values_equal
from luck_audit.schema import ToolSpec, specs_by_name
from luck_audit.trace import Trace

EVIDENCE_KINDS = ("user", "system", "tool_result", "chained")


@dataclass
class ArgProvenance:
    """Provenance of one required argument of one mutating call."""

    call_id: str
    tool: str
    arg: str
    value: Any
    status: str  # "evidenced" | "uninformed"
    source_kind: str | None = None  # one of EVIDENCE_KINDS, else None
    source_event_id: int | None = None
    source_field: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "tool": self.tool,
            "arg": self.arg,
            "value": self.value,
            "status": self.status,
            "source_kind": self.source_kind,
            "source_event_id": self.source_event_id,
            "source_field": self.source_field,
        }


@dataclass
class CallLedger:
    """The ledger for one mutating call: one entry per required arg."""

    call_id: str
    tool: str
    args: dict[str, Any] = field(default_factory=dict)
    entries: list[ArgProvenance] = field(default_factory=list)

    @property
    def uninformed_args(self) -> list[str]:
        return [e.arg for e in self.entries if e.status == "uninformed"]

    @property
    def is_lucky(self) -> bool:
        """A call is lucky when at least one required arg is uninformed."""
        return bool(self.uninformed_args)

    @property
    def evidence_coverage(self) -> float:
        if not self.entries:
            return 1.0
        evidenced = sum(1 for e in self.entries if e.status == "evidenced")
        return evidenced / len(self.entries)

    def to_dict(self) -> dict[str, Any]:
        return {
            "call_id": self.call_id,
            "tool": self.tool,
            "args": self.args,
            "is_lucky": self.is_lucky,
            "evidence_coverage": self.evidence_coverage,
            "entries": [e.to_dict() for e in self.entries],
        }


class EvidenceLedger:
    """Builds the provenance ledger for a whole trace.

    Calls are processed in trace order so chained provenance can only
    flow forward, from an earlier evidenced argument to a later one.
    Unknown tools (no spec) are skipped, never assumed mutating.
    """

    def __init__(self, specs: dict[str, ToolSpec] | list[ToolSpec] | tuple[ToolSpec, ...]):
        self.specs = specs if isinstance(specs, dict) else specs_by_name(list(specs))

    def build(self, trace: Trace) -> list[CallLedger]:
        # (call_id, arg) -> ArgProvenance for evidenced args only, so
        # later calls can chain through them.
        evidenced_args: dict[tuple[str, str], ArgProvenance] = {}
        ledgers: list[CallLedger] = []
        events = trace.events
        for index, event in enumerate(events):
            if event.kind != "tool_call":
                continue
            tool = str(event.data.get("tool", ""))
            spec = self.specs.get(tool)
            if spec is None or not spec.mutating:
                continue
            call_id = str(event.data.get("call_id", f"call-{event.event_id}"))
            args = dict(event.data.get("args", {}))
            ledger = CallLedger(call_id=call_id, tool=tool, args=args)
            for arg in spec.required_args:
                value = args.get(arg)
                entry = self._trace_arg(
                    trace, events, index, call_id, tool, arg, value, evidenced_args
                )
                ledger.entries.append(entry)
                if entry.status == "evidenced":
                    evidenced_args[(call_id, arg)] = entry
            ledgers.append(ledger)
        return ledgers

    def _trace_arg(
        self,
        trace: Trace,
        events: list,
        call_index: int,
        call_id: str,
        tool: str,
        arg: str,
        value: Any,
        evidenced_args: dict[tuple[str, str], ArgProvenance],
    ) -> ArgProvenance:
        base = ArgProvenance(
            call_id=call_id, tool=tool, arg=arg, value=value, status="uninformed"
        )
        if value is None:
            return base
        # 1. Declared system facts (checked first: they are timeless).
        for fact_name, fact_value in trace.system_facts.items():
            if values_equal(value, fact_value):
                base.status = "evidenced"
                base.source_kind = "system"
                base.source_field = fact_name
                return base
        # 2. Earlier spans, in trace order — earliest evidence wins.
        for event in events[:call_index]:
            if event.kind == "user":
                if value_in_text(value, event.text):
                    base.status = "evidenced"
                    base.source_kind = "user"
                    base.source_event_id = event.event_id
                    return base
            elif event.kind == "tool_result":
                result = event.data.get("result", {})
                field_path = find_in_structured(value, result)
                if field_path is not None:
                    base.status = "evidenced"
                    base.source_kind = "tool_result"
                    base.source_event_id = event.event_id
                    base.source_field = field_path
                    return base
                if value_in_text(value, event.text):
                    base.status = "evidenced"
                    base.source_kind = "tool_result"
                    base.source_event_id = event.event_id
                    return base
            elif event.kind == "tool_call":
                earlier_args = dict(event.data.get("args", {}))
                earlier_call_id = str(
                    event.data.get("call_id", f"call-{event.event_id}")
                )
                for earlier_arg, earlier_value in earlier_args.items():
                    if values_equal(value, earlier_value) and (
                        earlier_call_id,
                        earlier_arg,
                    ) in evidenced_args:
                        base.status = "evidenced"
                        base.source_kind = "chained"
                        base.source_event_id = event.event_id
                        base.source_field = earlier_arg
                        return base
            # "thought" and "final" events are never evidence.
        return base
