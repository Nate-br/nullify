"""Orchestrator — the single analysis entry point.

Every interface (CLI / TUI / Web) calls ``Orchestrator.run()`` and consumes the
shared ``EventBus``; no interface ever re-implements analysis logic
(PLAN.md §4.3).
"""

from __future__ import annotations

import logging
from typing import Any

from nullify.core.agents import (
    ClassificationAgent,
    DynamicAnalysisAgent,
    LogAnalysisAgent,
    LogCorrelationAgent,
    ReasoningAgent,
    StaticAnalysisAgent,
    TriageAgent,
)
from nullify.core.events import EventBus
from nullify.core.models import (
    AgentResult,
    AnalysisResult,
    FileTarget,
    LogTarget,
    ScanMode,
    Verdict,
)

log = logging.getLogger(__name__)


class Orchestrator:
    """Runs the agent pipeline over a target, streaming events as it goes."""

    def __init__(self, bus: EventBus | None = None) -> None:
        self.bus = bus or EventBus()
        self.listeners: list[AgentResult] = []

    # -- public API ----------------------------------------------------------
    def run(self, target: FileTarget | LogTarget, mode: ScanMode = ScanMode.STATIC_ONLY) -> AnalysisResult:
        result = AnalysisResult(target=target, mode=mode)

        if isinstance(target, LogTarget):
            stages: list = [LogCorrelationAgent, LogAnalysisAgent]
        else:
            stages = [TriageAgent, StaticAnalysisAgent, LogAnalysisAgent]

        if isinstance(target, FileTarget) and mode is ScanMode.DEEP:
            stages.append(DynamicAnalysisAgent)

        if isinstance(target, LogTarget):
            stages.append(ClassificationAgent)
            stages.append(ReasoningAgent)
        else:
            stages.append(ClassificationAgent)
            stages.append(ReasoningAgent)

        for stage_cls in stages:
            # Downstream agents receive upstream evidence via config.
            evidence = self._collect_evidence(result)
            agent = stage_cls(bus=self.bus, config={"evidence": evidence})
            agent_result = agent.run(target, mode)
            result.agent_results.append(agent_result)

            if agent_result.status.value == "failed":
                log.warning("agent %s failed: %s", agent_result.agent, agent_result.error)

        self._finalise(result)
        self.bus.scan_finished(result.verdict.value, result.malware_type, result.confidence)
        return result

    # -- helpers -------------------------------------------------------------
    @staticmethod
    def _collect_evidence(result: AnalysisResult) -> dict[str, Any]:
        """Flatten upstream agent results into the classifier/reasoner evidence dict."""
        evidence: dict[str, Any] = {"mode": result.mode.value}
        for ar in result.agent_results:
            if ar.agent == "Triage":
                evidence["hashes"] = ar.data.get("hashes")
                evidence["entropy"] = ar.data.get("entropy")
                evidence["packed"] = ar.data.get("packed", False)
                evidence["reputation"] = ar.data.get("reputation", {})
            elif ar.agent == "Static":
                evidence["type_votes"] = ar.data.get("type_votes", {})
        evidence["findings"] = [f.to_dict() for f in result.findings]
        return evidence

    @staticmethod
    def _finalise(result: AnalysisResult) -> None:
        classifier = result.agent("Classifier")
        reasoner = result.agent("Reasoning")

        if classifier and classifier.ok:
            result.verdict = Verdict(classifier.data["verdict"])
            result.malware_type = classifier.data["malware_type"]
            result.confidence = classifier.data["confidence"]

        mitre: set[str] = set()
        for f in result.findings:
            mitre.update(f.mitre_ids)
        result.mitre_ids = sorted(mitre)

        if reasoner and reasoner.ok:
            evidence = Orchestrator._collect_evidence(result)
            evidence.update({
                "verdict": result.verdict,
                "malware_type": result.malware_type,
                "confidence": result.confidence,
                "reasons": classifier.data.get("reasons", []) if classifier else [],
            })
            from nullify.core.agents.reasoning import build_explanation

            result.explanation = build_explanation(evidence)
        elif reasoner and reasoner.ok is False and reasoner.data.get("explanation"):
            result.explanation = reasoner.data["explanation"]
