"""End-to-end orchestrator tests over synthetic targets."""

from __future__ import annotations

from nullify.core.events import EventBus
from nullify.core.models import FileTarget, ScanMode
from nullify.core.orchestrator import Orchestrator


def test_file_scan_pipeline_complete(benign_file) -> None:
    res = Orchestrator(bus=EventBus()).run(benign_file, ScanMode.STATIC_ONLY)
    names = [ar.agent for ar in res.agent_results]
    assert names == ["Triage", "Static", "Classifier", "Reasoning"]
    assert res.verdict.value in ("benign", "suspicious")
    assert res.explanation  # reasoning produced a narration


def test_trojan_like_scan_flags(trojan_like_file) -> None:
    res = Orchestrator().run(trojan_like_file, ScanMode.STATIC_ONLY)
    assert res.verdict.value in ("suspicious", "malicious")
    assert res.malware_type in ("trojan", "unknown")
    assert res.mitre_ids  # ATT&CK ids collected from findings
    assert res.confidence > 0.0


def test_deep_mode_keeps_dynamic_stage(benign_file) -> None:
    res = Orchestrator().run(benign_file, ScanMode.DEEP)
    names = [ar.agent for ar in res.agent_results]
    assert "Dynamic" in names
    dynamic = res.agent("Dynamic")
    assert dynamic.status.value == "skipped"  # sandbox not configured → safe skip


def test_log_scan_pipeline(sysmon_log) -> None:
    res = Orchestrator().run(sysmon_log, ScanMode.STATIC_ONLY)
    names = [ar.agent for ar in res.agent_results]
    assert names == ["LogCorrelation", "Classifier", "Reasoning"]
    assert res.verdict.value in ("suspicious", "malicious")


def test_event_stream_flows() -> None:
    events: list[dict] = []
    bus = EventBus()
    bus.subscribe(events.append)
    import pathlib

    orch = Orchestrator(bus=bus)
    orch.run(FileTarget(pathlib.Path("/etc/hostname")), ScanMode.STATIC_ONLY)
    types = [e["type"] for e in events]
    assert "agent_started" in types
    assert "scan_finished" in types
    # every started agent completed
    started = sum(1 for t in types if t == "agent_started")
    completed = sum(1 for t in types if t == "agent_completed")
    assert started == completed
