"""Nullify core data models.

Every agent returns an ``AgentResult``; the orchestrator folds them into a single
``AnalysisResult`` that every interface (CLI / Web) consumes identically.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class Severity(str, Enum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Verdict(str, Enum):
    BENIGN = "benign"
    SUSPICIOUS = "suspicious"
    MALICIOUS = "malicious"
    UNKNOWN = "unknown"


class ScanMode(str, Enum):
    STATIC_ONLY = "static"
    DEEP = "deep"  # opt-in sandbox detonation


class AgentStatus(str, Enum):
    COMPLETED = "completed"
    SKIPPED = "skipped"
    FAILED = "failed"


MALWARE_TYPES: tuple[str, ...] = (
    "trojan",
    "ransomware",
    "spyware",
    "worm",
    "rootkit",
    "benign",
)


@dataclass(slots=True)
class Finding:
    """A single piece of evidence produced by an agent."""

    agent: str
    title: str
    detail: str = ""
    severity: Severity = Severity.INFO
    mitre_ids: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "title": self.title,
            "detail": self.detail,
            "severity": self.severity.value,
            "mitre_ids": list(self.mitre_ids),
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class FileTarget:
    """A file submitted for analysis."""

    path: Path

    def __post_init__(self) -> None:
        self.path = Path(self.path).resolve()

    @property
    def exists(self) -> bool:
        return self.path.is_file()

    @property
    def size_bytes(self) -> int:
        return self.path.stat().st_size

    def hashes(self) -> dict[str, str]:
        """Streaming md5/sha1/sha256 — no full-file reads into memory."""
        md5, sha1, sha256 = hashlib.md5(), hashlib.sha1(), hashlib.sha256()
        with self.path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                for h in (md5, sha1, sha256):
                    h.update(chunk)
        return {
            "md5": md5.hexdigest(),
            "sha1": sha1.hexdigest(),
            "sha256": sha256.hexdigest(),
        }

    def entropy(self, sample_size: int = 1_048_576) -> float | None:
        """Shannon entropy over up to ``sample_size`` bytes; None if unreadable."""
        import math

        try:
            data = self.path.open("rb").read(sample_size)
        except OSError:
            return None
        if not data:
            return 0.0
        freq = [0] * 256
        for byte in data:
            freq[byte] += 1
        n = len(data)
        return round(
            -sum((c / n) * math.log2(c / n) for c in freq if c), 3
        )

    def to_dict(self) -> dict[str, Any]:
        info: dict[str, Any] = {"path": str(self.path), "size_bytes": self.size_bytes}
        try:
            info["hashes"] = self.hashes()
        except OSError:
            pass
        return info


@dataclass(slots=True)
class LogTarget:
    """A behavioural log (Sysmon JSON-lines, EVTX export, text) for correlation."""

    path: Path
    records: list[dict[str, Any]] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.path = Path(self.path).resolve()

    @property
    def exists(self) -> bool:
        return self.path.is_file()

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "records_ingested": len(self.records),
        }


Target = FileTarget | LogTarget


@dataclass(slots=True)
class AgentResult:
    """Outcome of one agent's stage in the pipeline."""

    agent: str
    status: AgentStatus
    findings: list[Finding] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    duration_s: float = 0.0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.status is AgentStatus.COMPLETED

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent": self.agent,
            "status": self.status.value,
            "duration_s": round(self.duration_s, 3),
            "error": self.error,
            "data": self.data,
            "findings": [f.to_dict() for f in self.findings],
        }


@dataclass(slots=True)
class AnalysisResult:
    """The single object every interface renders."""

    target: Target
    mode: ScanMode
    started_at: float = field(default_factory=time.time)
    agent_results: list[AgentResult] = field(default_factory=list)
    verdict: Verdict = Verdict.UNKNOWN
    malware_type: str = "unknown"
    confidence: float = 0.0
    explanation: str = ""
    mitre_ids: list[str] = field(default_factory=list)

    @property
    def findings(self) -> list[Finding]:
        return [f for r in self.agent_results for f in r.findings]

    @property
    def duration_s(self) -> float:
        return time.time() - self.started_at

    def agent(self, name: str) -> AgentResult | None:
        return next((r for r in self.agent_results if r.agent == name), None)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target": self.target.to_dict(),
            "mode": self.mode.value,
            "duration_s": round(self.duration_s, 3),
            "verdict": self.verdict.value,
            "malware_type": self.malware_type,
            "confidence": round(self.confidence, 4),
            "mitre_ids": sorted(set(self.mitre_ids)),
            "explanation": self.explanation,
            "agents": [r.to_dict() for r in self.agent_results],
        }

    def to_json(self, indent: int | None = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)
