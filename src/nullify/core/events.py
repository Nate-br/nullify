"""Event bus — the one stream consumed by CLI, TUI and Web UI alike.

Agents publish progress here; interfaces subscribe. This is what makes
"one engine, three interfaces" true in practice.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)

Callback = Callable[[dict[str, Any]], None]


class EventBus:
    """Minimal synchronous pub/sub with error isolation per subscriber."""

    def __init__(self) -> None:
        self._subscribers: list[Callback] = []

    def subscribe(self, callback: Callback) -> None:
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callback) -> None:
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def emit(self, event_type: str, **payload: Any) -> None:
        event = {"type": event_type, **payload}
        for cb in list(self._subscribers):
            try:
                cb(event)
            except Exception:
                log.exception("event subscriber raised")

    # -- convenience wrappers ------------------------------------------------
    def agent_started(self, agent: str, **extra: Any) -> None:
        self.emit("agent_started", agent=agent, **extra)

    def agent_completed(self, agent: str, status: str, duration_s: float, **extra: Any) -> None:
        self.emit("agent_completed", agent=agent, status=status, duration_s=duration_s, **extra)

    def finding(self, agent: str, title: str, severity: str, **extra: Any) -> None:
        self.emit("finding", agent=agent, title=title, severity=severity, **extra)

    def scan_finished(self, verdict: str, malware_type: str, confidence: float) -> None:
        self.emit(
            "scan_finished",
            verdict=verdict,
            malware_type=malware_type,
            confidence=confidence,
        )
