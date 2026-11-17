"""Tests for the CLI."""

from luck_audit.__main__ import main


def test_demo_exits_zero(capsys):
    assert main(["demo"]) == 0
    out = capsys.readouterr().out
    assert "luck rate: 75.0%" in out


def test_generate_writes_traces(tmp_path):
    out = tmp_path / "traces.jsonl"
    assert main(["generate", "--n", "10", "--seed", "1", "--out", str(out)]) == 0
    assert out.exists()
    assert len(out.read_text(encoding="utf-8").strip().splitlines()) == 10


def test_audit_writes_reports(tmp_path):
    traces = tmp_path / "traces.jsonl"
    report = tmp_path / "report.md"
    data = tmp_path / "report.json"
    assert main(["generate", "--n", "20", "--seed", "2", "--out", str(traces)]) == 0
    assert (
        main(["audit", str(traces), "--report", str(report), "--json", str(data)]) == 0
    )
    assert "Luck Rate" in report.read_text(encoding="utf-8")
    assert data.exists()


def test_experiment_runs(capsys):
    assert main(["experiment", "--n", "20", "--seed", "3"]) == 0
    out = capsys.readouterr().out
    assert "measured luck rate" in out
