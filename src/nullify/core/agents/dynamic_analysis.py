"""Dynamic Analysis Agent — sandboxed detonation (opt-in, `--deep` only).

SAFETY BOUNDARY (non-negotiable, see AGENTS.md):
  * samples are NEVER executed on the host;
  * detonation happens only through the configured CAPEv2 sandbox
    (``NULLIFY_SANDBOX_URL``) and only in ScanMode.DEEP;
  * without a sandbox URL this agent reports ``skipped`` and the pipeline
    continues with static + classifier evidence.

Weeks 5–6 implement the real CAPEv2 REST submission and behaviour feature
extraction behind this same interface.
"""

from __future__ import annotations

import os

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


class DynamicAnalysisAgent(BaseAgent):
    """Submits the sample to CAPEv2 and extracts behavioural features."""

    name = "Dynamic"

    def analyze(self, target: Target, mode: ScanMode) -> AgentResult:
        if isinstance(target, LogTarget):
            return AgentResult(agent=self.name, status=AgentStatus.SKIPPED,
                               data={"reason": "log target — dynamic analysis not applicable"})

        sandbox_url = os.getenv("NULLIFY_SANDBOX_URL", "").strip()
        if mode is not ScanMode.DEEP:
            return AgentResult(agent=self.name, status=AgentStatus.SKIPPED,
                               data={"reason": "static scan — use --deep to opt in to sandboxing"})

        if not sandbox_url:
            return AgentResult(
                agent=self.name, status=AgentStatus.SKIPPED,
                data={"reason": "NULLIFY_SANDBOX_URL not configured — refusing to execute anything"},
            )

        # Weeks 5-6: CAPEv2 REST submission (POST /apiv2/tasks/create/file),
        # task polling, report fetch, behaviour feature extraction. The
        # never-execute-locally rule stays permanent.
        return AgentResult(
            agent=self.name, status=AgentStatus.SKIPPED,
            data={
                "reason": "CAPEv2 integration lands in weeks 5-6",
                "sandbox_url": sandbox_url,
            },
            findings=[Finding(
                agent=self.name,
                title="Dynamic analysis pending sandbox integration",
                severity=Severity.INFO,
            )],
        )
