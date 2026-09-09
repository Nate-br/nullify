"""Classification Agent — benign/malicious + type prediction.

Phase 0: transparent heuristic scorer over agent evidence (type votes from
static imports, severity-weighted findings, triage entropy). Weeks 7–8 swap in
an XGBoost model trained on EMBER behind the exact same ``classify()`` signature
(see docs/PLAN.md §6.3) — the orchestrator and interfaces won't change.
"""

from __future__ import annotations

from typing import Any

from nullify.core.agents.base import BaseAgent
from nullify.core.models import (
    AgentResult,
    AgentStatus,
    Finding,
    ScanMode,
    Severity,
    Target,
    Verdict,
)

SEVERITY_WEIGHTS: dict[Severity, float] = {
    Severity.INFO: 0.0,
    Severity.LOW: 1.0,
    Severity.MEDIUM: 2.5,
    Severity.HIGH: 5.0,
    Severity.CRITICAL: 9.0,
}

# Votes needed from static import hints to strongly suggest a type.
STRONG_TYPE_VOTES = 2
MALICIOUS_SCORE_THRESHOLD = 6.0
SUSPICIOUS_SCORE_THRESHOLD = 2.0


def classify(evidence: dict[str, Any]) -> dict[str, Any]:
    """Pure function: evidence dict → verdict/type/confidence + reasons.

    Kept side-effect-free so it is trivially testable and so the weeks 7–8
    XGBoost swap only replaces this function's internals.
    """
    reasons: list[str] = []
    score = 0.0

    # 1. Known-bad reputation is dominant evidence.
    reputation = evidence.get("reputation") or {}
    if reputation.get("known_malicious"):
        score += 10.0
        reasons.append("hash has known-bad reputation")

    # 2. Type votes from static import hints.
    type_votes: dict[str, int] = dict(evidence.get("type_votes") or {})
    best_type, best_votes = ("", 0)
    for mal_type, votes in type_votes.items():
        if votes > best_votes:
            best_type, best_votes = mal_type, votes
    if best_votes:
        score += min(best_votes * 1.5, 6.0)
        reasons.append(f"static imports suggest {best_type} ({best_votes} API hits)")

    # 3. Severity-weighted findings.
    for f in evidence.get("findings", []):
        try:
            sev = Severity(f.get("severity", "info"))
        except ValueError:
            sev = Severity.INFO
        score += SEVERITY_WEIGHTS.get(sev, 0.0)

    # 4. Packing raises suspicion but is not proof.
    if evidence.get("packed"):
        score += 2.0
        reasons.append("binary appears packed (high entropy)")

    verdict = Verdict.BENIGN
    if score >= MALICIOUS_SCORE_THRESHOLD:
        verdict = Verdict.MALICIOUS
    elif score >= SUSPICIOUS_SCORE_THRESHOLD:
        verdict = Verdict.SUSPICIOUS

    malware_type = "unknown"
    if verdict is Verdict.BENIGN:
        malware_type = "benign"
    elif best_votes >= STRONG_TYPE_VOTES and best_type:
        malware_type = best_type

    # Confidence: saturating mapping of score; type confidence needs votes.
    confidence = min(score / 15.0, 0.99) if verdict is not Verdict.BENIGN else max(
        0.5, min(0.9, 0.9 - score / 10.0)
    )
    if malware_type not in ("unknown", "benign"):
        confidence = max(confidence, min(0.6 + 0.1 * best_votes, 0.95))

    return {
        "verdict": verdict,
        "malware_type": malware_type,
        "confidence": round(confidence, 3),
        "score": round(score, 2),
        "reasons": reasons,
    }


class ClassificationAgent(BaseAgent):
    """Folds evidence from prior agents into a verdict + malware type."""

    name = "Classifier"

    def analyze(self, target: Target, mode: ScanMode) -> AgentResult:
        from nullify.core.models import AnalysisResult  # noqa: F401  (typing hook)

        evidence = self.config.get("evidence", {})
        if not evidence:
            return AgentResult(agent=self.name, status=AgentStatus.SKIPPED,
                               data={"reason": "no upstream evidence provided"})

        result = classify(evidence)
        findings = [
            Finding(
                agent=self.name,
                title=f"Heuristic score {result['score']}",
                detail="; ".join(result["reasons"]) or "no aggravating evidence",
                severity=_verdict_severity(result["verdict"]),
                metadata={"score": result["score"]},
            )
        ]

        return AgentResult(
            agent=self.name,
            status=AgentStatus.COMPLETED,
            findings=findings,
            data={
                "engine": "heuristic-phase0",
                "verdict": result["verdict"].value,
                "malware_type": result["malware_type"],
                "confidence": result["confidence"],
                "score": result["score"],
                "reasons": result["reasons"],
            },
        )


def _verdict_severity(verdict: Verdict) -> Severity:
    return {
        Verdict.MALICIOUS: Severity.CRITICAL,
        Verdict.SUSPICIOUS: Severity.MEDIUM,
        Verdict.BENIGN: Severity.INFO,
        Verdict.UNKNOWN: Severity.LOW,
    }[verdict]
