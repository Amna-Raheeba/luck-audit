"""Run-level audit and aggregate metrics.

A run's verdict:
  - "failed": the run itself failed. Luck is not assessed — a failed
    run is not a lucky pass.
  - "lucky": the run succeeded AND at least one mutating call has an
    uninformed required argument. The outcome was right; the evidence
    was not there.
  - "competent": the run succeeded and every mutating call is fully
    evidenced.

Headline metric — Luck Rate = lucky successful runs / all successful
runs. A benchmark that reports 95% success with a 40% luck rate is
reporting 57% competent success. The auditor also reports its own
accuracy against injected ground truth when the traces carry it, so
the numbers below are never taken on trust.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from luck_audit.provenance import CallLedger, EvidenceLedger
from luck_audit.risk import aggregate_risk, run_risk_score
from luck_audit.schema import BOOKING_TOOLS, ToolSpec, specs_by_name
from luck_audit.trace import Trace


@dataclass
class RunAudit:
    """Audit of one trace."""

    run_id: str
    outcome: str
    verdict: str  # "competent" | "lucky" | "failed"
    ledgers: list[CallLedger] = field(default_factory=list)
    # Risk-weighted luck score of this run (see luck_audit/risk.py):
    # risk weight of its lucky mutating calls / risk weight of all its
    # mutating calls. None when the run made no mutating calls.
    risk_score: float | None = None

    @property
    def is_lucky(self) -> bool:
        return self.verdict == "lucky"

    @property
    def mutating_calls(self) -> int:
        return len(self.ledgers)

    @property
    def lucky_calls(self) -> int:
        return sum(1 for ledger in self.ledgers if ledger.is_lucky)

    @property
    def evidence_coverage(self) -> float:
        entries = [e for ledger in self.ledgers for e in ledger.entries]
        if not entries:
            return 1.0
        evidenced = sum(1 for e in entries if e.status == "evidenced")
        return evidenced / len(entries)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "outcome": self.outcome,
            "verdict": self.verdict,
            "mutating_calls": self.mutating_calls,
            "lucky_calls": self.lucky_calls,
            "evidence_coverage": self.evidence_coverage,
            "risk_score": self.risk_score,
            "ledgers": [ledger.to_dict() for ledger in self.ledgers],
        }


def audit_trace(
    trace: Trace,
    specs: dict[str, ToolSpec] | list[ToolSpec] | tuple[ToolSpec, ...] = BOOKING_TOOLS,
) -> RunAudit:
    """Audit one trace against the tool specs."""
    specs_map = specs if isinstance(specs, dict) else specs_by_name(list(specs))
    ledgers = EvidenceLedger(specs_map).build(trace)
    if trace.outcome == "failure":
        verdict = "failed"
    elif any(ledger.is_lucky for ledger in ledgers):
        verdict = "lucky"
    else:
        verdict = "competent"
    return RunAudit(
        run_id=trace.run_id,
        outcome=trace.outcome,
        verdict=verdict,
        ledgers=ledgers,
        risk_score=run_risk_score(ledgers, specs_map),
    )


@dataclass
class AggregateMetrics:
    """Metrics over a set of audited runs. All counts, no estimates."""

    total_runs: int
    successful_runs: int
    failed_runs: int
    lucky_runs: int
    competent_runs: int
    luck_rate: float | None  # lucky / successful; None if no successes
    competent_success_rate: float | None  # competent / total
    total_mutating_calls: int
    lucky_calls: int
    uninformed_call_rate: float | None
    uninformed_rate_by_tool: dict[str, float]
    uninformed_rate_by_arg: dict[str, float]
    auditor_precision: float | None  # vs injected ground truth
    auditor_recall: float | None
    auditor_accuracy: float | None
    ground_truth_calls: int
    # Risk-weighted luck (see luck_audit/risk.py). The aggregate score
    # is over successful runs only, mirroring the Luck Rate.
    risk_weighted_luck_score: float | None
    uninformed_rate_by_tier: dict[str, float]
    risk_weight_by_tier: dict[str, float]
    lucky_weight: float
    total_weight: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "failed_runs": self.failed_runs,
            "lucky_runs": self.lucky_runs,
            "competent_runs": self.competent_runs,
            "luck_rate": self.luck_rate,
            "competent_success_rate": self.competent_success_rate,
            "total_mutating_calls": self.total_mutating_calls,
            "lucky_calls": self.lucky_calls,
            "uninformed_call_rate": self.uninformed_call_rate,
            "uninformed_rate_by_tool": self.uninformed_rate_by_tool,
            "uninformed_rate_by_arg": self.uninformed_rate_by_arg,
            "auditor_precision": self.auditor_precision,
            "auditor_recall": self.auditor_recall,
            "auditor_accuracy": self.auditor_accuracy,
            "ground_truth_calls": self.ground_truth_calls,
            "risk_weighted_luck_score": self.risk_weighted_luck_score,
            "uninformed_rate_by_tier": self.uninformed_rate_by_tier,
            "risk_weight_by_tier": self.risk_weight_by_tier,
            "lucky_weight": self.lucky_weight,
            "total_weight": self.total_weight,
        }


def _rate(numerator: int, denominator: int) -> float | None:
    return numerator / denominator if denominator else None


def aggregate(
    audits: list[RunAudit],
    traces: list[Trace] | None = None,
    specs: dict[str, ToolSpec] | list[ToolSpec] | tuple[ToolSpec, ...] = BOOKING_TOOLS,
) -> AggregateMetrics:
    """Aggregate run audits. Pass the traces too for ground-truth scoring.

    `specs` supplies the risk tiers for the risk-weighted metrics; it
    must be the same specs the audits were built with.
    """
    total = len(audits)
    successful = [a for a in audits if a.outcome == "success"]
    lucky = [a for a in successful if a.is_lucky]
    competent = [a for a in successful if not a.is_lucky]

    all_ledgers = [ledger for a in audits for ledger in a.ledgers]
    total_calls = len(all_ledgers)
    lucky_calls = sum(1 for ledger in all_ledgers if ledger.is_lucky)

    by_tool: dict[str, list[int]] = {}
    by_arg: dict[str, list[int]] = {}
    for ledger in all_ledgers:
        by_tool.setdefault(ledger.tool, [0, 0])
        by_tool[ledger.tool][1] += 1
        if ledger.is_lucky:
            by_tool[ledger.tool][0] += 1
        for entry in ledger.entries:
            key = f"{ledger.tool}.{entry.arg}"
            by_arg.setdefault(key, [0, 0])
            by_arg[key][1] += 1
            if entry.status == "uninformed":
                by_arg[key][0] += 1
    uninformed_by_tool = {
        tool: _rate(counts[0], counts[1]) or 0.0 for tool, counts in by_tool.items()
    }
    uninformed_by_arg = {
        arg: _rate(counts[0], counts[1]) or 0.0 for arg, counts in by_arg.items()
    }

    precision = recall = accuracy = None
    gt_calls = 0
    if traces:
        tp = fp = fn = tn = 0
        by_run = {a.run_id: a for a in audits}
        for trace in traces:
            audit = by_run.get(trace.run_id)
            if audit is None:
                continue
            predicted = {
                (ledger.call_id, entry.arg): entry.status
                for ledger in audit.ledgers
                for entry in ledger.entries
            }
            for call_id, args in trace.ground_truth.items():
                for arg, truth in args.items():
                    if (call_id, arg) not in predicted:
                        continue
                    gt_calls += 1
                    pred_uninformed = predicted[(call_id, arg)] == "uninformed"
                    true_uninformed = truth == "uninformed"
                    if pred_uninformed and true_uninformed:
                        tp += 1
                    elif pred_uninformed and not true_uninformed:
                        fp += 1
                    elif not pred_uninformed and true_uninformed:
                        fn += 1
                    else:
                        tn += 1
        if gt_calls:
            precision = _rate(tp, tp + fp)
            recall = _rate(tp, tp + fn)
            accuracy = _rate(tp + tn, tp + fp + fn + tn)

    risk = aggregate_risk(audits, specs)

    return AggregateMetrics(
        total_runs=total,
        successful_runs=len(successful),
        failed_runs=total - len(successful),
        lucky_runs=len(lucky),
        competent_runs=len(competent),
        luck_rate=_rate(len(lucky), len(successful)),
        competent_success_rate=_rate(len(competent), total),
        total_mutating_calls=total_calls,
        lucky_calls=lucky_calls,
        uninformed_call_rate=_rate(lucky_calls, total_calls),
        uninformed_rate_by_tool=uninformed_by_tool,
        uninformed_rate_by_arg=uninformed_by_arg,
        auditor_precision=precision,
        auditor_recall=recall,
        auditor_accuracy=accuracy,
        ground_truth_calls=gt_calls,
        risk_weighted_luck_score=risk["risk_weighted_luck_score"],
        uninformed_rate_by_tier=risk["uninformed_rate_by_tier"],
        risk_weight_by_tier=risk["risk_weight_by_tier"],
        lucky_weight=risk["lucky_weight"],
        total_weight=risk["total_weight"],
    )
