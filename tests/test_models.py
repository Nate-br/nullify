"""Tests for core data models."""

from __future__ import annotations

import json

from nullify.core.models import (
    AgentResult,
    AgentStatus,
    AnalysisResult,
    FileTarget,
    Finding,
    LogTarget,
    ScanMode,
    Severity,
)


def test_file_hashes_are_stable(benign_file: FileTarget) -> None:
    h1 = benign_file.hashes()
    h2 = benign_file.hashes()
    assert h1 == h2
    assert set(h1) == {"md5", "sha1", "sha256"}
    assert len(h1["sha256"]) == 64


def test_entropy_bounds(benign_file: FileTarget) -> None:
    ent = benign_file.entropy()
    assert ent is not None
    assert 0.0 <= ent <= 8.0


def test_entropy_of_missing_file_is_none(missing_file: FileTarget) -> None:
    assert missing_file.entropy() is None


def test_log_target_roundtrip(sysmon_log: LogTarget) -> None:
    assert sysmon_log.exists
    assert "records_ingested" in sysmon_log.to_dict()


def test_finding_to_dict() -> None:
    f = Finding(agent="X", title="t", severity=Severity.HIGH, mitre_ids=("T1059",))
    d = f.to_dict()
    assert d["severity"] == "high"
    assert d["mitre_ids"] == ["T1059"]
    json.dumps(d)  # must be JSON-serialisable


def test_agent_result_ok() -> None:
    ok = AgentResult(agent="a", status=AgentStatus.COMPLETED)
    skipped = AgentResult(agent="a", status=AgentStatus.SKIPPED)
    assert ok.ok
    assert not skipped.ok


def test_analysis_result_findings_flatten() -> None:
    r1 = AgentResult(agent="a", status=AgentStatus.COMPLETED,
                     findings=[Finding(agent="a", title="one")])
    r2 = AgentResult(agent="b", status=AgentStatus.COMPLETED,
                     findings=[Finding(agent="b", title="two")])
    res = AnalysisResult(target=FileTarget("/etc/hostname"), mode=ScanMode.STATIC_ONLY,
                         agent_results=[r1, r2])
    assert [f.title for f in res.findings] == ["one", "two"]
    d = res.to_dict()
    assert d["verdict"] == "unknown"
    json.dumps(d)
