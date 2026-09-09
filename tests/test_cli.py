"""CLI tests via typer's CliRunner."""

from __future__ import annotations

import json

from typer.testing import CliRunner

from nullify.interfaces.cli.main import app

runner = CliRunner()


def test_help() -> None:
    out = runner.invoke(app, ["--help"])
    assert out.exit_code == 0
    assert "scan" in out.output


def test_scan_json(benign_file) -> None:
    out = runner.invoke(app, ["scan", str(benign_file.path), "--json"])
    assert out.exit_code == 0, out.output
    # JSON is the last blob printed; find the outermost object.
    start = out.output.index("{")
    data = json.loads(out.output[start:])
    assert data["verdict"] in ("benign", "suspicious")
    assert data["mode"] == "static"
    assert any(a["agent"] == "Classifier" for a in data["agents"])


def test_scan_missing_file_errors() -> None:
    out = runner.invoke(app, ["scan", "/nonexistent/definitely_missing.exe"])
    assert out.exit_code != 0


def test_batch_directory(benign_file, tmp_path) -> None:
    out = runner.invoke(app, ["batch", str(benign_file.path.parent),
                              "-o", str(tmp_path / "report.json")])
    assert out.exit_code == 0, out.output
    report = json.loads((tmp_path / "report.json").read_text())
    assert len(report["results"]) >= 1


def test_analyze_log_json(sysmon_log) -> None:
    out = runner.invoke(app, ["analyze-log", str(sysmon_log.path), "--json"])
    assert out.exit_code == 0, out.output
    start = out.output.index("{")
    data = json.loads(out.output[start:])
    assert "T1053" in data["mitre_ids"]
