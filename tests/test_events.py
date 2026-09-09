"""Tests for the event bus."""

from __future__ import annotations

from nullify.core.events import EventBus


def test_pubsub_basic() -> None:
    bus = EventBus()
    seen: list[dict] = []
    bus.subscribe(seen.append)
    bus.emit("finding", agent="X", title="t")
    assert seen == [{"type": "finding", "agent": "X", "title": "t"}]


def test_broken_subscriber_does_not_kill_others() -> None:
    bus = EventBus()
    seen: list[dict] = []

    def boom(_event: dict) -> None:
        raise RuntimeError("subscriber bug")

    bus.subscribe(boom)
    bus.subscribe(seen.append)
    bus.agent_started("Triage")
    assert len(seen) == 1


def test_unsubscribe() -> None:
    bus = EventBus()
    seen: list[dict] = []
    cb = seen.append
    bus.subscribe(cb)
    bus.unsubscribe(cb)
    bus.emit("finding")
    assert seen == []
