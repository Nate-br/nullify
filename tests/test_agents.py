"""Agent-level tests. All targets are synthetic — no real malware, ever."""

from __future__ import annotations

from nullify.core.agents import (
    ClassificationAgent,
    LogCorrelationAgent,
    ReasoningAgent,
    StaticAnalysisAgent,
    TriageAgent,
)
from nullify.core.models import FileTarget, ScanMode


def test_triage_pe_detection(pe_like_file) -> None:
    res = TriageAgent().run(pe_like_file, ScanMode.STATIC_ONLY)
    assert res.ok
    assert res.data["file_magic"] == "pe"
    assert res.data["reputation"]["checked"] is False  # no API key in tests
    assert res.data["entropy"] is not None


def test_triage_missing_file_fails_gracefully(missing_file) -> None:
    res = TriageAgent().run(missing_file, ScanMode.STATIC_ONLY)
    assert res.status.value == "failed"
    assert "not found" in res.error


def test_triage_skips_log_targets(sysmon_log) -> None:
    res = TriageAgent().run(sysmon_log, ScanMode.STATIC_ONLY)
    assert res.status.value == "skipped"


def test_static_finds_import_hints(trojan_like_file) -> None:
    res = StaticAnalysisAgent().run(trojan_like_file, ScanMode.STATIC_ONLY)
    assert res.ok
    assert res.data["type_votes"].get("trojan", 0) >= 2
    titles = [f.title for f in res.findings]
    assert any("CreateRemoteThread" in t for t in titles)


def test_static_finds_run_key_persistence(trojan_like_file) -> None:
    res = StaticAnalysisAgent().run(trojan_like_file, ScanMode.STATIC_ONLY)
    titles = [f.title for f in res.findings]
    assert any("Run-key" in t for t in titles)


def test_static_skips_log_targets(sysmon_log) -> None:
    res = StaticAnalysisAgent().run(sysmon_log, ScanMode.STATIC_ONLY)
    assert res.status.value == "skipped"


def test_dynamic_never_runs_without_sandbox(pe_like_file) -> None:
    from nullify.core.agents import DynamicAnalysisAgent

    res = DynamicAnalysisAgent().run(pe_like_file, ScanMode.DEEP)
    assert res.status.value == "skipped"  # no NULLIFY_SANDBOX_URL → refuses
    res2 = DynamicAnalysisAgent().run(pe_like_file, ScanMode.STATIC_ONLY)
    assert res2.status.value == "skipped"  # not in deep mode


def test_log_correlation_maps_attack(sysmon_log) -> None:
    res = LogCorrelationAgent().run(sysmon_log, ScanMode.STATIC_ONLY)
    assert res.ok
    assert "T1053" in res.data["techniques"]          # schtasks /create
    assert "T1547.001" in res.data["techniques"]      # Run key
    assert res.data["records_ingested"] == 4          # junk line skipped
    assert any("suspicious path" in f.title.lower() for f in res.findings)


def test_log_correlation_skips_file_targets(pe_like_file) -> None:
    res = LogCorrelationAgent().run(pe_like_file, ScanMode.STATIC_ONLY)
    assert res.status.value == "skipped"


def test_classifier_evidence_flow(trojan_like_file) -> None:
    triage = TriageAgent().run(trojan_like_file, ScanMode.STATIC_ONLY)
    static = StaticAnalysisAgent().run(trojan_like_file, ScanMode.STATIC_ONLY)
    evidence = {
        "mode": "static",
        "packed": triage.data.get("packed", False),
        "reputation": triage.data.get("reputation", {}),
        "type_votes": static.data.get("type_votes", {}),
        "findings": [f.to_dict() for f in (triage.findings + static.findings)],
    }
    res = ClassificationAgent(config={"evidence": evidence}).run(trojan_like_file, ScanMode.STATIC_ONLY)
    assert res.ok
    assert res.data["verdict"] in ("suspicious", "malicious")
    assert res.data["malware_type"] in ("trojan", "unknown")


def test_classifier_without_evidence_skips(pe_like_file) -> None:
    # Force no-model mode so the test is hermetic even when the real
    # models/malware_xgb.json exists — the skip contract is about evidence.
    res = ClassificationAgent(model_path="/nonexistent/model.json").run(
        pe_like_file, ScanMode.STATIC_ONLY
    )
    assert res.status.value == "skipped"


def test_reasoning_template_output(trojan_like_file) -> None:
    evidence = {
        "verdict": "suspicious",
        "malware_type": "trojan",
        "confidence": 0.6,
        "reasons": ["static imports suggest trojan (3 API hits)"],
        "findings": [{"agent": "Static", "title": "Suspicious import: WinExec",
                      "severity": "medium"}],
        "mode": "static",
    }
    res = ReasoningAgent(config={"evidence": evidence}).run(trojan_like_file, ScanMode.STATIC_ONLY)
    assert res.ok
    assert "SUSPICIOUS" in res.data["explanation"]
    assert res.data["requests_deep_analysis"] is False


def test_reasoning_requests_deep_when_unconfident(pe_like_file) -> None:
    evidence = {"verdict": "unknown", "malware_type": "unknown", "confidence": 0.1,
                "reasons": [], "findings": [], "mode": "static"}
    res = ReasoningAgent(config={"evidence": evidence}).run(pe_like_file, ScanMode.STATIC_ONLY)
    assert res.data["requests_deep_analysis"] is True


def test_reasoning_malicious_unknown_type(pe_like_file) -> None:
    evidence = {
        "verdict": "malicious", "malware_type": "unknown", "confidence": 0.85,
        "reasons": ["heuristic findings exceed threshold"],
        "findings": [], "mode": "static",
    }
    res = ReasoningAgent(config={"evidence": evidence}).run(pe_like_file, ScanMode.STATIC_ONLY)
    assert res.ok
    assert "MALICIOUS" in res.data["explanation"]
    assert "exhibits malicious characteristics" in res.data["explanation"]
    assert "inconclusive" not in res.data["explanation"]


def test_triage_detects_elf(tmp_path) -> None:
    elf = tmp_path / "sample.bin"
    elf.write_bytes(b"\x7fELF\x02\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x3e\x00")
    target = FileTarget(path=str(elf))
    res = TriageAgent().run(target, ScanMode.STATIC_ONLY)
    assert res.ok
    assert res.data["file_magic"] == "elf"
    assert any("Linux ELF" in f.title for f in res.findings)


def test_static_with_pefile(trojan_like_file, monkeypatch) -> None:
    import pefile

    class MockImp:
        name = b"CreateRemoteThread"

    class MockEntry:
        def __init__(self) -> None:
            self.imports = [MockImp()]

    class MockPE:
        def __init__(self, path):
            self.DIRECTORY_ENTRY_IMPORT = [MockEntry()]

    monkeypatch.setattr(pefile, "PE", MockPE)
    res = StaticAnalysisAgent().run(trojan_like_file, ScanMode.STATIC_ONLY)
    assert res.ok
    assert "pefile" in res.data.get("engine", "")
    titles = [f.title for f in res.findings]
    assert any("CreateRemoteThread" in t for t in titles)


def test_static_with_capa(trojan_like_file, monkeypatch) -> None:
    import json
    import subprocess

    orig_run = subprocess.run
    def mock_run(cmd, *args, **kwargs):
        if cmd and cmd[0] == "capa":
            class MockRes:
                returncode = 0
                stdout = json.dumps({
                    "rules": {
                        "inject thread": {
                            "meta": {
                                "description": "injects a thread",
                                "att&ck": [{"id": "T1055.003"}]
                            }
                        }
                    }
                })
            return MockRes()
        return orig_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", mock_run)
    res = StaticAnalysisAgent().run(trojan_like_file, ScanMode.STATIC_ONLY)
    assert res.ok
    assert "capa" in res.data.get("engine", "")
    titles = [f.title for f in res.findings]
    assert any("capa: inject thread" in t for t in titles)

def test_static_yara_matches_trojan(trojan_like_file) -> None:
    res = StaticAnalysisAgent().run(trojan_like_file, ScanMode.STATIC_ONLY)
    assert res.ok
    assert "yara+" in res.data.get("engine", "")
    assert "yara_matches" in res.data
    titles = [f.title for f in res.findings]
    assert any("Generic_Trojan_Dropper" in t for t in titles)

def test_static_yara_skips_benign(benign_file) -> None:
    res = StaticAnalysisAgent().run(benign_file, ScanMode.STATIC_ONLY)
    assert res.ok
    # Not a PE, so no yara matches
    assert "yara+" not in res.data.get("engine", "")
    titles = [f.title for f in res.findings]
    assert not any("Generic_Trojan_Dropper" in t for t in titles)
