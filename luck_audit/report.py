"""Report generation: markdown and JSON summaries of an audit run."""

from __future__ import annotations

import json

from luck_audit.audit import AggregateMetrics, RunAudit


def _pct(value: float | None) -> str:
    return f"{value:.1%}" if value is not None else "n/a"


def markdown_report(metrics: AggregateMetrics, audits: list[RunAudit]) -> str:
    """A human-readable markdown report. Numbers only, no adjectives."""
    lines = [
        "# Luck Audit Report",
        "",
        "## Summary",
        "",
        f"- Total runs: {metrics.total_runs}",
        f"- Successful runs: {metrics.successful_runs}",
        f"- Failed runs: {metrics.failed_runs}",
        f"- Lucky runs (success without evidence): {metrics.lucky_runs}",
        f"- Competent runs: {metrics.competent_runs}",
        f"- **Luck Rate: {_pct(metrics.luck_rate)}** (lucky / successful)",
        f"- Competent success rate: {_pct(metrics.competent_success_rate)}",
        f"- Mutating calls: {metrics.total_mutating_calls} "
        f"({metrics.lucky_calls} lucky, "
        f"uninformed-call rate {_pct(metrics.uninformed_call_rate)})",
        f"- **Risk-Weighted Luck Score: {_pct(metrics.risk_weighted_luck_score)}** "
        f"(lucky risk weight {metrics.lucky_weight:.1f} / "
        f"total {metrics.total_weight:.1f})",
        "",
        "## Uninformed rate by risk tier",
        "",
    ]
    for tier, rate in sorted(metrics.uninformed_rate_by_tier.items()):
        lines.append(
            f"- {tier}: {_pct(rate)} "
            f"(share of total risk weight: "
            f"{_pct(metrics.risk_weight_by_tier.get(tier))})"
        )
    lines += ["", "## Uninformed rate by tool", ""]
    for tool, rate in sorted(metrics.uninformed_rate_by_tool.items()):
        lines.append(f"- {tool}: {_pct(rate)}")
    lines += ["", "## Uninformed rate by argument", ""]
    for arg, rate in sorted(metrics.uninformed_rate_by_arg.items()):
        lines.append(f"- {arg}: {_pct(rate)}")
    if metrics.ground_truth_calls:
        lines += [
            "",
            "## Auditor accuracy (vs injected ground truth)",
            "",
            f"- Ground-truth labelled arguments: {metrics.ground_truth_calls}",
            f"- Precision: {_pct(metrics.auditor_precision)}",
            f"- Recall: {_pct(metrics.auditor_recall)}",
            f"- Accuracy: {_pct(metrics.auditor_accuracy)}",
        ]
    lucky_runs = [a for a in audits if a.is_lucky]
    if lucky_runs:
        lines += ["", "## Lucky runs", ""]
        for audit in lucky_runs:
            calls = ", ".join(
                f"{ledger.tool} ({', '.join(ledger.uninformed_args)})"
                for ledger in audit.ledgers
                if ledger.is_lucky
            )
            lines.append(f"- {audit.run_id}: {calls}")
    lines.append("")
    return "\n".join(lines)


def json_report(metrics: AggregateMetrics, audits: list[RunAudit]) -> str:
    """Machine-readable report: metrics plus per-run verdicts."""
    return json.dumps(
        {
            "metrics": metrics.to_dict(),
            "runs": [audit.to_dict() for audit in audits],
        },
        indent=2,
    )
