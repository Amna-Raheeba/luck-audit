"""Luck Audit — post-hoc evidence-sufficiency audit for agent traces.

A successful agent run is not trustworthy if a mutating tool call was
made without the evidence needed to choose it correctly. This package
audits a recorded trace and reports the share of passes that were lucky,
not competent. Policy-free and domain-general: it checks whether each
required argument of each mutating call can be traced to an earlier
evidence span (a user message, a tool result, or a declared system
fact) — or whether the agent guessed.

The agent's own reasoning never counts as evidence: a value that
appears only in the model's thoughts is, by definition, uninformed.
"""

__version__ = "0.2.0"

from luck_audit.audit import aggregate, audit_trace
from luck_audit.provenance import ArgProvenance, CallLedger, EvidenceLedger
from luck_audit.risk import aggregate_risk, run_risk_score
from luck_audit.schema import RISK_TIERS, RISK_WEIGHTS, ToolSpec, risk_weight
from luck_audit.trace import Trace, TraceEvent

__all__ = [
    "__version__",
    "Trace",
    "TraceEvent",
    "ToolSpec",
    "EvidenceLedger",
    "ArgProvenance",
    "CallLedger",
    "audit_trace",
    "aggregate",
    "run_risk_score",
    "aggregate_risk",
    "risk_weight",
    "RISK_TIERS",
    "RISK_WEIGHTS",
]
