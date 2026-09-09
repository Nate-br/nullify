"""Reasoning Agent — synthesises evidence into a plain-English verdict.

Phase 0: deterministic template narration over structured evidence. Week 11
adds the optional LLM path (Anthropic API) — it receives structured evidence
JSON only, never raw binary content (hard rule, see AGENTS.md).
"""

from __future__ import annotations

import os
from typing import Any

from nullify.core.agents.base import BaseAgent
from nullify.core.models import (
    AgentResult,
    AgentStatus,
    LogTarget,
    ScanMode,
    Target,
    Verdict,
)

_TYPE_SENTENCES: dict[str, str] = {
    "trojan": "behaviour is consistent with a Remote Access Trojan (installer/loader APIs "
              "combined with network egress indicators)",
    "ransomware": "behaviour is consistent with ransomware (crypto APIs plus mass file "
                  "enumeration or ransom-note strings)",
    "spyware": "behaviour is consistent with spyware (input-hooks, screen or clipboard "
               "capture APIs)",
    "worm": "behaviour is consistent with a worm (self-copy and network-share enumeration "
            "APIs)",
    "rootkit": "behaviour is consistent with rootkit capability (driver loading and kernel "
               "object manipulation APIs)",
    "benign": "no significant malicious indicators were found",
    "unknown": "evidence was inconclusive; treat as suspicious pending further analysis",
}


def build_explanation(evidence: dict[str, Any]) -> str:
    """Pure function: evidence dict → plain-English explanation."""
    verdict = evidence.get("verdict", Verdict.UNKNOWN)
    mal_type = evidence.get("malware_type", "unknown")
    confidence = float(evidence.get("confidence", 0.0))
    reasons: list[str] = list(evidence.get("reasons", []))
    findings = evidence.get("findings", [])

    lines: list[str] = []
    headline = {
        Verdict.MALICIOUS: f"Verdict: MALICIOUS ({mal_type}, confidence {confidence:.0%}).",
        Verdict.SUSPICIOUS: f"Verdict: SUSPICIOUS (confidence {confidence:.0%}).",
        Verdict.BENIGN: "Verdict: BENIGN.",
        Verdict.UNKNOWN: "Verdict: UNKNOWN.",
    }[verdict]
    lines.append(headline)

    if mal_type in _TYPE_SENTENCES:
        lines.append(f"This sample's {_TYPE_SENTENCES[mal_type]}.")

    if reasons:
        lines.append("Key evidence: " + "; ".join(reasons[:4]) + ".")

    high = [f for f in findings if str(f.get("severity")) in ("high", "critical")]
    if high:
        cited = "; ".join(f"{f.get('agent')}: {f.get('title')}" for f in high[:5])
        lines.append(f"High-severity findings — {cited}.")

    deep = evidence.get("mode") == "deep"
    if deep:
        lines.append("Analysis included opt-in sandbox detonation.")
    else:
        lines.append("Static-only analysis: rerun with --deep (sandbox configured) to add "
                     "behavioural evidence.")
    return "\n".join(lines)


class ReasoningAgent(BaseAgent):
    """Narrates the verdict; optional LLM upgrade path stays behind this interface."""

    name = "Reasoning"

    def analyze(self, target: Target, mode: ScanMode) -> AgentResult:
        evidence = self.config.get("evidence", {})
        if not evidence:
            return AgentResult(agent=self.name, status=AgentStatus.SKIPPED,
                               data={"reason": "no upstream evidence provided"})

        explanation = build_explanation(evidence)
        engine = "template-phase0"

        # Week 11: optional LLM synthesis. Structured evidence only — never bytes.
        if os.getenv("ANTHROPIC_API_KEY", "").strip():
            explanation += "\n(LLM-enhanced narration lands in week 11; template used for now.)"

        # Escalation hook: low confidence requests deeper analysis next run.
        request_deep = (
            float(evidence.get("confidence", 0.0)) < 0.5
            and mode is ScanMode.STATIC_ONLY
            and not isinstance(target, LogTarget)
        )

        return AgentResult(
            agent=self.name,
            status=AgentStatus.COMPLETED,
            data={
                "engine": engine,
                "explanation": explanation,
                "requests_deep_analysis": request_deep,
            },
        )
