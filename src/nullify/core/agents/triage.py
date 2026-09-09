"""Triage agent — cheap first-pass filtering.

Computes hashes, file type and entropy, and decides whether the sample is worth
escalating to deeper analysis. Reputation lookups (VirusTotal / MalwareBazaar)
are optional and degrade gracefully when no API key is configured.
"""

from __future__ import annotations

import os
from typing import Any

from nullify.core.agents.base import BaseAgent
from nullify.core.models import (
    AgentResult,
    AgentStatus,
    FileTarget,
    Finding,
    LogTarget,
    ScanMode,
    Severity,
    Target,
)

# Simple executable/script extension filter used for quick filtering.
EXECUTABLE_EXTENSIONS: frozenset[str] = frozenset({
    ".exe", ".dll", ".scr", ".com", ".pif", ".sys", ".drv",
    ".ps1", ".bat", ".cmd", ".vbs", ".vbe", ".js", ".jse", ".wsf", ".hta",
    ".msi", ".docm", ".xlsm", ".pptm", ".lnk",
})

PACKED_ENTROPY_THRESHOLD = 7.2
HIGH_ENTROPY_THRESHOLD = 7.8


class TriageAgent(BaseAgent):
    """Hash / file-type / entropy first pass."""

    name = "Triage"

    def analyze(self, target: Target, mode: ScanMode) -> AgentResult:
        findings: list[Finding] = []
        data: dict[str, Any] = {}

        if isinstance(target, LogTarget):
            return AgentResult(
                agent=self.name, status=AgentStatus.SKIPPED,
                data={"reason": "log target — triage not applicable"},
            )

        if not target.exists:
            return AgentResult(
                agent=self.name, status=AgentStatus.FAILED,
                error=f"file not found: {target.path}",
            )

        hashes = target.hashes()
        data["hashes"] = hashes
        data["size_bytes"] = target.size_bytes

        suffix = target.path.suffix.lower()
        data["extension"] = suffix
        looks_executable = suffix in EXECUTABLE_EXTENSIONS

        # Magic-byte sniff for extension-less or mislabelled files.
        magic = self._sniff_magic(target)
        data["file_magic"] = magic
        if magic == "pe":
            looks_executable = True
            findings.append(Finding(
                agent=self.name, title="Windows PE executable",
                detail="MZ header detected", severity=Severity.INFO,
            ))

        entropy = target.entropy()
        data["entropy"] = entropy
        packed = False
        if entropy is not None and looks_executable:
            if entropy >= HIGH_ENTROPY_THRESHOLD:
                packed = True
                findings.append(Finding(
                    agent=self.name, title="Very high entropy — likely packed/encrypted",
                    detail=f"entropy={entropy} (≥{HIGH_ENTROPY_THRESHOLD})",
                    severity=Severity.MEDIUM, mitre_ids=("T1027",),
                    metadata={"entropy": entropy},
                ))
            elif entropy >= PACKED_ENTROPY_THRESHOLD:
                findings.append(Finding(
                    agent=self.name, title="Elevated entropy — possibly packed",
                    detail=f"entropy={entropy} (≥{PACKED_ENTROPY_THRESHOLD})",
                    severity=Severity.LOW, mitre_ids=("T1027",),
                    metadata={"entropy": entropy},
                ))

        reputation = self._reputation_lookup(hashes["sha256"])
        data["reputation"] = reputation
        if reputation.get("known_malicious"):
            findings.append(Finding(
                agent=self.name, title="Hash has known-bad reputation",
                detail=f"source={reputation.get('source')}",
                severity=Severity.CRITICAL,
            ))

        data["escalate"] = True
        data["packed"] = packed
        data["looks_executable"] = looks_executable

        self._finding("Triage complete", f"entropy={entropy}", "info")
        return AgentResult(agent=self.name, status=AgentStatus.COMPLETED,
                           findings=findings, data=data)

    # -- internals -----------------------------------------------------------
    @staticmethod
    def _sniff_magic(target: FileTarget) -> str | None:
        try:
            with target.path.open("rb") as fh:
                head = fh.read(2)
        except OSError:
            return None
        if head == b"MZ":
            return "pe"
        if head == b"\x7fELF":
            return "elf"
        return None

    @staticmethod
    def _reputation_lookup(sha256: str) -> dict[str, Any]:
        """Optional VT lookup; explicitly non-blocking and keyless-safe."""
        if not os.getenv("VIRUSTOTAL_API_KEY", "").strip():
            return {"checked": False, "reason": "no VIRUSTOTAL_API_KEY configured"}
        # Network lookups are intentionally NOT implemented in the Phase-0 scaffold;
        # weeks 3-4 work adds them behind this same interface.
        return {"checked": False, "reason": "reputation lookup lands in weeks 3-4", "sha256": sha256}
