"""Static Analysis Agent — inspect the file without executing it.

Phase 0 ships a dependency-free heuristic layer (import-table hints, suspicious
strings, script content). Weeks 3–4 replace it with pefile + capa + YARA behind
the same interface.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from nullify.core.agents.base import BaseAgent
from nullify.core.models import (
    AgentResult,
    AgentStatus,
    Finding,
    LogTarget,
    ScanMode,
    Severity,
    Target,
)

# --- heuristic tables (static indicators per malware type, from PLAN.md §6.1) ---
IMPORT_HINTS: dict[str, tuple[str, ...]] = {
    "trojan": (
        "URLDownloadToFile", "WinExec", "CreateRemoteThread",
        "ShellExecute", "InternetOpenUrl", "WSAStartup", "InternetConnect",
    ),
    "spyware": (
        "SetWindowsHookEx", "GetAsyncKeyState", "BitBlt",
        "GetClipboardData", "GetKeyState", "WaveOut",
    ),
    "ransomware": (
        "CryptEncrypt", "CryptGenKey", "CryptAcquireContext",
        "FindFirstFile", "WriteFile", "DeleteFile",
    ),
    "worm": (
        "WNetOpenEnum", "WNetEnumResource", "NetShareEnum",
        "CreateFile", "CopyFile",
    ),
    "rootkit": (
        "DeviceIoControl", "NtLoadDriver", "ZwLoadDriver",
        "OpenSCManager", "CreateService",
    ),
}

# MITRE ATT&CK mapping for specific APIs (interpretability layer, PLAN.md §6.3).
API_TO_MITRE: dict[str, str] = {
    "CreateRemoteThread": "T1055",     # Process Injection
    "URLDownloadToFile": "T1105",      # Ingress Tool Transfer
    "WinExec": "T1059",                # Command and Scripting Interpreter
    "SetWindowsHookEx": "T1056.001",   # Keylogging
    "GetAsyncKeyState": "T1056.001",
    "BitBlt": "T1113",                 # Screen Capture
    "CryptEncrypt": "T1486",           # Data Encrypted for Impact
    "CryptGenKey": "T1486",
    "FindFirstFile": "T1083",          # File and Directory Discovery
    "WNetOpenEnum": "T1135",           # Network Share Discovery
    "NetShareEnum": "T1135",
    "NtLoadDriver": "T1547.003",       # Boot Autostart: Kernel Drivers
    "ZwLoadDriver": "T1547.003",
    "CreateService": "T1543.003",      # System Process: Windows Service
}

SUSPICIOUS_PATTERNS: tuple[tuple[str, re.Pattern[str], Severity], ...] = (
    ("Registry Run-key persistence",
     re.compile(r"Software\\+Microsoft\\+Windows\\+CurrentVersion\\+Run", re.IGNORECASE),
     Severity.HIGH),
    ("Scheduled task creation",
     re.compile(r"schtasks(?:\.exe)?.*?/create|ITaskService", re.IGNORECASE),
     Severity.MEDIUM),
    ("PowerShell download cradle",
     re.compile(r"(?:powershell|pwsh).{0,40}?(?:-enc|downloadstring|downloadfile|iex|invoke-expression)",
                re.IGNORECASE | re.DOTALL),
     Severity.HIGH),
    ("Hardcoded public IP address",
     re.compile(r"\b(?:[1-9]|[1-9]\d|1\d\d|2[0-4]\d|25[0-5])\.(?:\d{1,3})\.(?:\d{1,3})\.(?:\d{1,3})\b"),
     Severity.MEDIUM),
    ("Executable drop path",
     re.compile(r"(?:%?(?:APPDATA|TEMP|ProgramData)\\\\?|%?SYSTEM32\\\\?)[\w\-. ]+\.(?:exe|dll|scr|bat|ps1)",
                re.IGNORECASE),
     Severity.MEDIUM),
    ("Ransom note string",
     re.compile(r"your files (?:have been|are) encrypted|readme[-_ ]?for[-_ ]?decrypt"
                r"|send\s+(?:\d+\s?(?:btc|bitcoin|xmr|monero))", re.IGNORECASE),
     Severity.CRITICAL),
)

SCRIPT_EXTENSIONS: frozenset[str] = frozenset({".ps1", ".bat", ".cmd", ".vbs", ".js", ".hta"})
MAX_STRING_BYTES = 4 * 1024 * 1024  # scan first 4 MiB of strings

log = logging.getLogger(__name__)


class StaticAnalysisAgent(BaseAgent):
    """Non-executing inspection: imports, strings, patterns."""

    name = "Static"

    def analyze(self, target: Target, mode: ScanMode) -> AgentResult:
        if isinstance(target, LogTarget):
            return AgentResult(agent=self.name, status=AgentStatus.SKIPPED,
                               data={"reason": "log target — static analysis not applicable"})

        findings: list[Finding] = []
        data: dict[str, Any] = {}

        blob = self._read_strings(target)
        is_pe = self._is_pe(target)
        data["is_pe"] = is_pe

        # 1. Import-table hints — PE-only: the Windows API names below also occur
        #    as innocuous strings inside ELF/Linux binaries (e.g. libc symbols),
        #    which caused false positives before this gate.
        type_votes: dict[str, int] = {}
        pe_imports = None

        if is_pe:
            # 1. Real import-table parsing via pefile, fallback to heuristics
            try:
                import pefile
                pe = pefile.PE(target.path)
                if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
                    pe_imports = set()
                    for entry in pe.DIRECTORY_ENTRY_IMPORT:
                        for imp in entry.imports:
                            if imp.name:
                                pe_imports.add(imp.name.decode("ascii", errors="ignore"))
            except Exception as e:  # noqa: BLE001 — any parse failure falls back
                log.debug("pefile parse failed (%s); using raw-string heuristics", e)

            for mal_type, apis in IMPORT_HINTS.items():
                if pe_imports is not None:
                    hits = [api for api in apis if api in pe_imports]
                else:
                    hits = [api for api in apis if api.encode() in blob]
                
                if hits:
                    data[f"imports_{mal_type}"] = hits
                    for api in hits:
                        mitre = API_TO_MITRE.get(api)
                        findings.append(Finding(
                            agent=self.name,
                            title=f"Suspicious import: {api}",
                            detail=f"associated with {mal_type} behaviour",
                            severity=Severity.MEDIUM,
                            mitre_ids=(mitre,) if mitre else (),
                            metadata={"type_hint": mal_type, "api": api},
                        ))
                    type_votes[mal_type] = len(hits)
        data["type_votes"] = type_votes

        # 2. Capability detection via flare-capa, fallback to behavioral string patterns
        capa_success = False
        if is_pe:
            try:
                import json
                import subprocess

                import capa  # noqa: F401 - verify it's installed
                
                res = subprocess.run(
                    ["capa", "-j", str(target.path)],
                    capture_output=True, text=True, check=False, timeout=90,
                )
                if res.returncode == 0:
                    capa_doc = json.loads(res.stdout)
                    rules = capa_doc.get("rules", {})
                    for rule_name, rule_data in rules.items():
                        meta = rule_data.get("meta", {})
                        if meta.get("lib") or meta.get("is_subscope"):
                            continue
                        
                        attack = meta.get("att&ck", [])
                        mitre_ids = [m.get("id") for m in attack if "id" in m]
                        
                        findings.append(Finding(
                            agent=self.name,
                            title=f"capa: {rule_name}",
                            detail=meta.get("description", "Capability detected"),
                            severity=Severity.HIGH,
                            mitre_ids=tuple(mitre_ids)
                        ))
                    capa_success = True
                    data["engine"] = "pefile-capa" if pe_imports is not None else "heuristic-capa"
            except Exception as e:  # noqa: BLE001 — capa is optional; degrade gracefully
                log.debug("capa unavailable/failed (%s); using string patterns", e)

        if not capa_success:
            # Fallback to suspicious patterns
            try:
                text = blob.decode("utf-8", errors="ignore")
            except Exception:  # noqa: BLE001 — decode is best-effort
                text = ""
            for title, pattern, severity in SUSPICIOUS_PATTERNS:
                match = pattern.search(text)
                if match:
                    findings.append(Finding(
                        agent=self.name, title=title,
                        detail=f"matched: …{match.group(0)[:80]}…",
                        severity=severity,
                    ))

        data["engine"] = (
            "pefile-capa" if capa_success and pe_imports is not None
            else "pefile-heuristic" if pe_imports is not None
            else "heuristic-capa" if capa_success
            else "heuristic-phase0"
        )

        data["findings_count"] = len(findings)
        if not findings:
            findings.append(Finding(agent=self.name, title="No static indicators found",
                                    severity=Severity.INFO))
        return AgentResult(agent=self.name, status=AgentStatus.COMPLETED,
                           findings=findings, data=data)

    # -- internals -----------------------------------------------------------
    @staticmethod
    def _is_pe(target: Target) -> bool:
        try:
            with target.path.open("rb") as fh:
                return fh.read(2) == b"MZ"
        except OSError:
            return False

    @staticmethod
    def _read_strings(target: Target) -> bytes:
        """Read up to MAX_STRING_BYTES; extract ASCII+UTF-16LE-ish strings."""
        try:
            raw = target.path.open("rb").read(MAX_STRING_BYTES)
        except OSError:
            return b""
        # UTF-16: drop NUL bytes between ASCII chars to make imports searchable.
        widened = raw.replace(b"\x00", b"")
        return raw + b"\n" + widened
