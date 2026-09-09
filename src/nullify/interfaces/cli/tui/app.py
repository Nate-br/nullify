"""Textual TUI app — week 12 milestone."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from rich.text import Text
from textual import work
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, Label, Log, Static

from nullify.core.events import EventBus
from nullify.core.models import FileTarget, ScanMode, Severity, Verdict
from nullify.core.orchestrator import Orchestrator

log = logging.getLogger(__name__)

_VERDICT_STYLE = {
    Verdict.MALICIOUS.value: "bold red",
    Verdict.SUSPICIOUS.value: "bold yellow",
    Verdict.BENIGN.value: "bold green",
    Verdict.UNKNOWN.value: "bold white",
}
_SEV_STYLE = {
    Severity.CRITICAL.value: "bold red",
    Severity.HIGH.value: "red",
    Severity.MEDIUM.value: "yellow",
    Severity.LOW.value: "cyan",
    Severity.INFO.value: "dim",
}


class VerdictBanner(Static):
    """Banner showing the final verdict."""


class NullifyTUI(App):
    """Nullify interactive TUI."""

    CSS = """
    #agent_progress {
        width: 30%;
        border: solid cyan;
        padding: 1;
    }
    #findings_log {
        width: 70%;
        border: solid cyan;
    }
    VerdictBanner {
        height: 3;
        border: solid cyan;
        content-align: center middle;
    }
    """

    BINDINGS = [  # noqa: RUF012
        ("q", "quit", "Quit"),
        ("r", "run_scan", "Run Scan"),
    ]

    def __init__(self, target_path: str = "", deep: bool = False, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.target_path = target_path
        self.deep = deep
        self.bus = EventBus()
        self.bus.subscribe(self.handle_event)
        self.orchestrator = Orchestrator(bus=self.bus)
        self.agent_labels = {
            "Triage": "○ Triage",
            "Static": "○ Static Analysis",
            "Dynamic": "○ Dynamic Analysis",
            "LogCorrelation": "○ Log Correlation",
            "Classifier": "○ Classification",
            "Reasoning": "○ Reasoning",
        }

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(value=self.target_path, placeholder="Target path", id="target_input")
        with Horizontal():
            with Vertical(id="agent_progress"):
                yield Label("Pipeline Progress", classes="panel-title")
                for agent, text in self.agent_labels.items():
                    yield Label(text, id=f"prog_{agent}")
            yield Log(id="findings_log")
        yield VerdictBanner("Ready", id="verdict_banner")
        yield Footer()

    def on_mount(self) -> None:
        if self.target_path:
            self.action_run_scan()

    def action_run_scan(self) -> None:
        inp = self.query_one("#target_input", Input)
        path_str = inp.value
        if not path_str:
            self.notify("No target path provided.", severity="error")
            return

        self.query_one("#findings_log", Log).clear()
        self.query_one("#verdict_banner", VerdictBanner).update("Scanning...")
        
        for agent, text in self.agent_labels.items():
            self.query_one(f"#prog_{agent}", Label).update(text)

        mode = ScanMode.DEEP if self.deep else ScanMode.STATIC_ONLY
        self.run_scan_worker(path_str, mode)

    @work(exclusive=True, thread=True)
    def run_scan_worker(self, path: str, mode: ScanMode) -> None:
        try:
            self.orchestrator.run(FileTarget(Path(path)), mode)
        except Exception as exc:  # noqa: BLE001
            self.call_from_thread(self.notify, f"Error scanning: {exc}", severity="error")
            self.call_from_thread(self.query_one("#verdict_banner", VerdictBanner).update, f"Error: {exc}")

    def handle_event(self, event: dict[str, Any]) -> None:
        self.call_from_thread(self._process_event, event)

    def _process_event(self, event: dict[str, Any]) -> None:
        etype = event.get("type")
        if etype == "agent_started":
            agent = event.get("agent", "")
            lbl = self.query(f"#prog_{agent}")
            if lbl:
                base_text = self.agent_labels.get(agent, agent)
                lbl.first().update(f"[yellow]⟳ {base_text[2:]}[/yellow]")
        elif etype == "agent_completed":
            agent = event.get("agent", "")
            status = event.get("status", "")
            lbl = self.query(f"#prog_{agent}")
            if lbl:
                base_text = self.agent_labels.get(agent, agent)[2:]
                if status == "completed":
                    lbl.first().update(f"[green]✓ {base_text}[/green]")
                elif status == "skipped":
                    lbl.first().update(f"[dim]○ {base_text} (skipped)[/dim]")
                else:
                    lbl.first().update(f"[red]✗ {base_text}[/red]")
        elif etype == "finding":
            severity = event.get("severity", "info")
            title = event.get("title", "")
            agent = event.get("agent", "")
            style = _SEV_STYLE.get(severity, "dim")
            self.query_one("#findings_log", Log).write_line(Text.from_markup(f"• [{style}][{agent}][/] {title}"))
        elif etype == "scan_finished":
            verdict = event.get("verdict", "unknown")
            score = event.get("confidence", 0.0)
            engine = event.get("malware_type", "unknown")
            style = _VERDICT_STYLE.get(verdict, "white")
            banner_text = f"[{style}]{verdict.upper()}[/{style}] | Type: {engine} | Score: {score:.0%}"
            self.query_one("#verdict_banner", VerdictBanner).update(Text.from_markup(banner_text))

if __name__ == "__main__":
    app = NullifyTUI()
    app.run()
