"""Agent contract shared by every stage of the pipeline."""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

from nullify.core.models import AgentResult, AgentStatus

if TYPE_CHECKING:
    from nullify.core.events import EventBus
    from nullify.core.models import ScanMode, Target

log = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all pipeline agents.

    Contract (see docs/PLAN.md §12 for safety rules):
      * never ``print()`` — emit progress on the bus;
      * never raise for soft failures — return ``status="skipped"/"failed"``;
      * return an :class:`AgentResult` no matter what.
    """

    name: str = "agent"

    def __init__(self, bus: EventBus | None = None, config: dict[str, Any] | None = None) -> None:
        self.bus = bus
        self.config: dict[str, Any] = config or {}

    # -- helpers -------------------------------------------------------------
    def _emit(self, event: str, **payload: Any) -> None:
        if self.bus is not None:
            self.bus.emit(event, **payload)

    def _finding(self, title: str, detail: str = "", severity: str = "info", **extra: Any) -> None:
        if self.bus is not None:
            self.bus.emit("finding", agent=self.name, title=title, detail=detail,
                          severity=severity, **extra)

    # -- template method -----------------------------------------------------
    def run(self, target: Target, mode: ScanMode) -> AgentResult:
        self._emit("agent_started", agent=self.name)
        started = time.time()
        try:
            result = self.analyze(target, mode)
        except Exception as exc:
            log.exception("agent %s crashed", self.name)
            duration = time.time() - started
            self._emit("agent_completed", agent=self.name, status="failed",
                       duration_s=duration, error=str(exc))
            return AgentResult(
                agent=self.name,
                status=AgentStatus.FAILED,
                duration_s=duration,
                error=f"{type(exc).__name__}: {exc}",
            )
        result.duration_s = time.time() - started
        self._emit("agent_completed", agent=self.name, status=result.status.value,
                   duration_s=result.duration_s)
        return result

    @abstractmethod
    def analyze(self, target: Target, mode: ScanMode) -> AgentResult:
        """Run this agent's analysis. Must return an AgentResult."""
        raise NotImplementedError
