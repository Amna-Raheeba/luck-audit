"""CLI: generate traces, audit them, run the demo, run experiments.

Usage:
    python -m luck_audit demo
    python -m luck_audit generate --n 100 --lucky 0.4 --seed 7 --out traces.jsonl
    python -m luck_audit audit traces.jsonl [--report report.md] [--json report.json]
    python -m luck_audit experiment --n 200 --lucky 0.4 --seed 7
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from luck_audit.audit import aggregate, audit_trace
from luck_audit.mock import demo_traces, generate_dataset
from luck_audit.report import json_report, markdown_report
from luck_audit.trace import read_traces, write_traces


def _print_metrics(metrics) -> None:
    print(f"runs: {metrics.total_runs}  success: {metrics.successful_runs}  "
          f"failed: {metrics.failed_runs}")
    print(f"lucky runs: {metrics.lucky_runs}  competent runs: {metrics.competent_runs}")
    luck = metrics.luck_rate
    print(f"luck rate: {luck:.1%}" if luck is not None else "luck rate: n/a (no successes)")
    print(f"mutating calls: {metrics.total_mutating_calls}  "
          f"lucky calls: {metrics.lucky_calls}")
    rwls = metrics.risk_weighted_luck_score
    print(f"risk-weighted luck score: {rwls:.1%}" if rwls is not None
          else "risk-weighted luck score: n/a (no mutating calls)")
    if metrics.ground_truth_calls:
        print(f"auditor vs ground truth ({metrics.ground_truth_calls} labelled args): "
              f"precision {metrics.auditor_precision:.1%}  "
              f"recall {metrics.auditor_recall:.1%}  "
              f"accuracy {metrics.auditor_accuracy:.1%}")


def cmd_demo(_args: argparse.Namespace) -> int:
    traces = demo_traces()
    audits = [audit_trace(t) for t in traces]
    for trace, audit in zip(traces, audits):
        print(f"{trace.run_id}: outcome={trace.outcome} verdict={audit.verdict} "
              f"coverage={audit.evidence_coverage:.0%}")
        for ledger in audit.ledgers:
            for entry in ledger.entries:
                source = entry.source_kind or "none"
                print(f"  {ledger.tool}.{entry.arg} = {entry.value!r}: "
                      f"{entry.status} (source: {source})")
    metrics = aggregate(audits, traces)
    print()
    _print_metrics(metrics)
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    traces = generate_dataset(n=args.n, lucky_rate=args.lucky, wrong_rate=args.wrong, seed=args.seed)
    write_traces(traces, args.out)
    print(f"wrote {len(traces)} traces to {args.out}")
    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    traces = read_traces(args.traces)
    audits = [audit_trace(t) for t in traces]
    metrics = aggregate(audits, traces)
    _print_metrics(metrics)
    if args.report:
        Path(args.report).write_text(markdown_report(metrics, audits), encoding="utf-8")
        print(f"wrote markdown report to {args.report}")
    if args.json:
        Path(args.json).write_text(json_report(metrics, audits), encoding="utf-8")
        print(f"wrote JSON report to {args.json}")
    return 0


def cmd_experiment(args: argparse.Namespace) -> int:
    """Sweep the lucky rate and report how the luck rate responds."""
    rows = []
    for lucky_rate in (0.0, 0.2, 0.4, 0.6, 0.8):
        traces = generate_dataset(n=args.n, lucky_rate=lucky_rate, wrong_rate=0.1, seed=args.seed)
        audits = [audit_trace(t) for t in traces]
        metrics = aggregate(audits, traces)
        rows.append({
            "lucky_rate_injected": lucky_rate,
            "total_runs": metrics.total_runs,
            "successful_runs": metrics.successful_runs,
            "lucky_runs": metrics.lucky_runs,
            "luck_rate_measured": metrics.luck_rate,
            "auditor_accuracy": metrics.auditor_accuracy,
        })
        print(f"injected lucky rate {lucky_rate:.1f} -> measured luck rate "
              f"{metrics.luck_rate:.1%} (n={metrics.total_runs}, "
              f"auditor accuracy {metrics.auditor_accuracy:.1%})")
    if args.out:
        Path(args.out).write_text(json.dumps(rows, indent=2), encoding="utf-8")
        print(f"wrote sweep to {args.out}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="luck-audit")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("demo", help="audit one trace per mode and print the ledgers")

    gen = sub.add_parser("generate", help="generate a trace dataset")
    gen.add_argument("--n", type=int, default=100)
    gen.add_argument("--lucky", type=float, default=0.4)
    gen.add_argument("--wrong", type=float, default=0.1)
    gen.add_argument("--seed", type=int, default=7)
    gen.add_argument("--out", default="traces.jsonl")

    aud = sub.add_parser("audit", help="audit a JSONL trace file")
    aud.add_argument("traces")
    aud.add_argument("--report", default=None)
    aud.add_argument("--json", default=None)

    exp = sub.add_parser("experiment", help="sweep injected lucky rate, measure luck rate")
    exp.add_argument("--n", type=int, default=200)
    exp.add_argument("--seed", type=int, default=7)
    exp.add_argument("--out", default=None)

    args = parser.parse_args(argv)
    if args.command == "demo":
        return cmd_demo(args)
    if args.command == "generate":
        return cmd_generate(args)
    if args.command == "audit":
        return cmd_audit(args)
    if args.command == "experiment":
        return cmd_experiment(args)
    parser.error(f"unknown command {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
