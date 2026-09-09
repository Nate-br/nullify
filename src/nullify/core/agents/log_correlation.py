"""Log Correlation Agent — behavioural log analysis + ATT&CK mapping.

Phase 0 supports JSON-lines (Sysmon-style events) and plain-text logs. Weeks
9–10 add native EVTX parsing and DARPA/Mordor dataset ingestion.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any

from nullify.core.agents.base import BaseAgent
from nullify.core.models import (
    AgentResult,
    AgentStatus,
    FileTarget,
    Finding,
    ScanMode,
    Severity,
    Target,
)

# ATT&CK technique detection over log content (case-insensitive).
TECHNIQUE_SIGNATURES: tuple[tuple[str, str, re.Pattern[str], Severity], ...] = (
    ("T1059", "Command and Scripting Interpreter",
     re.compile(r"\b(?:powershell|pwsh|cmd\.exe|wscript|cscript)\b", re.IGNORECASE), Severity.MEDIUM),
    ("T1053", "Scheduled Task/Job",
     re.compile(r"\bschtasks\b|Register-ScheduledTask|/create\b.*(?:/sc|/tn)", re.IGNORECASE), Severity.HIGH),
    ("T1547.001", "Registry Run Keys / Startup Folder",
     re.compile(r"CurrentVersion\\\\+Run", re.IGNORECASE), Severity.HIGH),
    ("T1003.001", "LSASS Memory (credential dumping)",
     re.compile(r"lsass\.exe|comsvcs\.dll.*?MiniDump|rundll32.*?comsvcs", re.IGNORECASE), Severity.CRITICAL),
    ("T1021", "Remote Services (lateral movement)",
     re.compile(r"\b(?:psexec|wmic.*?process call|winrm|wsmprovhost)\b", re.IGNORECASE), Severity.HIGH),
    ("T1071", "Application Layer Protocol (C2)",
     re.compile(r"\b(?:http|dns|icmp)\b.{0,30}\b(?:beacon|c2|callback)\b", re.IGNORECASE), Severity.MEDIUM),
    ("T1486", "Data Encrypted for Impact (ransomware)",
     re.compile(r"\.encrypted\b|README_FOR_DECRYPT|ransom", re.IGNORECASE), Severity.CRITICAL),
)

SUSPICIOUS_IMAGE_RE = re.compile(
    r"(?:\\AppData\\|\\Temp\\|\\ProgramData\\|\\Users\\Public\\)[\w\-. ]+\.(?:exe|dll|scr|ps1)", re.IGNORECASE
)


class LogCorrelationAgent(BaseAgent):
    """Parses behavioural logs and maps activity to MITRE ATT&CK techniques."""

    name = "LogCorrelation"

    def analyze(self, target: Target, mode: ScanMode) -> AgentResult:
        if isinstance(target, FileTarget):
            return AgentResult(agent=self.name, status=AgentStatus.SKIPPED,
                               data={"reason": "file target — use `nullify analyze-log` for logs"})

        records = self._load_records(target.path)
        data: dict[str, Any] = {"records_ingested": len(records)}
        findings: list[Finding] = []

        if not records:
            return AgentResult(agent=self.name, status=AgentStatus.FAILED,
                               error="no records could be parsed from log")

        blob = json.dumps(records, default=str)

        # 1. ATT&CK technique matching.
        matched: list[str] = []
        for tid, name, pattern, severity in TECHNIQUE_SIGNATURES:
            hits = len(pattern.findall(blob))
            if hits:
                matched.append(tid)
                findings.append(Finding(
                    agent=self.name,
                    title=f"ATT&CK {tid}: {name}",
                    detail=f"{hits} matching event(s) in log",
                    severity=severity,
                    mitre_ids=(tid,),
                    metadata={"hit_count": hits},
                ))
        data["techniques"] = matched

        # 2. Process-tree anomaly: suspicious image paths.
        images = Counter()
        for rec in records:
            img = str(rec.get("image") or rec.get("Image") or rec.get("process", {}).get("image", ""))
            if img and SUSPICIOUS_IMAGE_RE.search(img):
                images[img] += 1
        if images:
            data["suspicious_images"] = dict(images.most_common(10))
            for img, count in images.most_common(5):
                findings.append(Finding(
                    agent=self.name, title="Process launched from suspicious path",
                    detail=f"{img} ×{count}", severity=Severity.HIGH,
                    mitre_ids=("T1059",),
                ))

        # 3. Top noisy processes (context for the reasoning agent).
        proc_counts = Counter(
            str(r.get("process", r.get("image", "unknown"))) for r in records
        )
        data["top_processes"] = dict(proc_counts.most_common(5))

        if not findings:
            findings.append(Finding(agent=self.name, title="No suspicious activity detected in log",
                                    severity=Severity.INFO))
        return AgentResult(agent=self.name, status=AgentStatus.COMPLETED,
                           findings=findings, data=data)

    # -- internals -----------------------------------------------------------
    @staticmethod
    def _load_records(path) -> list[dict[str, Any]]:
        """JSON-lines first; fall back to one-record-per-line JSON scan."""
        records: list[dict[str, Any]] = []
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(obj, dict):
                        records.append(obj)
        except OSError:
            return []
        return records
