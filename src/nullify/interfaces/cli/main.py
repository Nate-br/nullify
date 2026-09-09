"""Nullify command-line interface.

Commands:
    scan          analyse a file (static by default, --deep for opt-in sandbox)
    analyze-log   correlate a behavioural log (Sysmon JSONL, text)
    batch         scan every file in a directory, optional JSON report

All commands call the shared Orchestrator — no analysis logic lives here
(PLAN.md §4.3).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from nullify import __version__
from nullify.core.events import EventBus
from nullify.core.models import (
    AnalysisResult,
    FileTarget,
    LogTarget,
    ScanMode,
    Severity,
    Verdict,
)
from nullify.core.orchestrator import Orchestrator

app = typer.Typer(
    name="nullify",
    help="Agentic AI-powered malware & malware-type detection system.",
    no_args_is_help=True,
    add_completion=False,
)
log_app = typer.Typer(help="Log-analysis utilities.", no_args_is_help=True)
app.add_typer(log_app, name="log")

console = Console()
err_console = Console(stderr=True)

_VERDICT_STYLE = {
    Verdict.MALICIOUS: "bold red",
    Verdict.SUSPICIOUS: "bold yellow",
    Verdict.BENIGN: "bold green",
    Verdict.UNKNOWN: "bold white",
}
_SEV_ORDER = {
    Severity.CRITICAL: 0,
    Severity.HIGH: 1,
    Severity.MEDIUM: 2,
    Severity.LOW: 3,
    Severity.INFO: 4,
}
_SEV_STYLE = {
    Severity.CRITICAL: "bold red",
    Severity.HIGH: "red",
    Severity.MEDIUM: "yellow",
    Severity.LOW: "cyan",
    Severity.INFO: "dim",
}


def _setup_verbose() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")


def _make_stream_printer() -> object:
    """CLI narration in the plan's style: [Agent]  summary."""
    def printer(event: dict) -> None:
        etype = event.get("type")
        if etype == "agent_started":
            console.print(f"[dim]▸ {event['agent']} running…[/dim]")
        elif etype == "finding":
            style = _SEV_STYLE.get(Severity(event.get("severity", "info")), "dim")
            console.print(f"  • [{style}]({event.get('agent')}) {event['title']}[/{style}]")
        elif etype == "agent_completed":
            status = event.get("status", "")
            icon = {"completed": "✓", "skipped": "○", "failed": "✗"}.get(status, "·")
            console.print(f"[dim]{icon} {event['agent']} {status}[/dim]")
        elif etype == "scan_finished":
            console.print()
    return printer


def _render_result(res: AnalysisResult, show_findings: bool = True) -> None:
    table = Table(show_header=True, header_style="bold", show_edge=False)
    table.add_column("Field", style="bold", no_wrap=True)
    table.add_column("Value")

    tstyle = _VERDICT_STYLE.get(res.verdict, "bold white")
    table.add_row("Target", str(res.target.path))
    table.add_row("Mode", res.mode.value)
    table.add_row("Verdict", f"[{tstyle}]{res.verdict.value.upper()}[/{tstyle}]")
    table.add_row("Type", res.malware_type)
    table.add_row("Confidence", f"{res.confidence:.0%}")
    table.add_row("Duration", f"{res.duration_s:.2f}s")
    if res.mitre_ids:
        table.add_row("ATT&CK", ", ".join(res.mitre_ids))
    console.print(table)

    if show_findings:
        findings = sorted(res.findings, key=lambda f: _SEV_ORDER.get(f.severity, 99))
        ft = Table(show_header=True, header_style="bold", show_edge=False, pad_edge=False)
        ft.add_column("Severity", no_wrap=True)
        ft.add_column("Finding", max_width=60)
        ft.add_column("Detail")
        for f in findings[:15]:
            style = _SEV_STYLE.get(f.severity, "dim")
            ft.add_row(
                f"[{style}]{f.severity.value.upper()}[/{style}]",
                f.title,
                f.detail[:70],
            )
        if len(findings) > 15:
            ft.add_row("", f"… and {len(findings) - 15} more", "")
        console.print(ft)

    if res.explanation:
        console.print(Panel(res.explanation, title="Reasoning", border_style="cyan"))


def _build_orchestrator(stream: bool) -> Orchestrator:
    bus = EventBus()
    if stream:
        bus.subscribe(_make_stream_printer())  # type: ignore[arg-type]
    return Orchestrator(bus=bus)


def _run_file_scan(path: Path, mode: ScanMode, stream: bool) -> AnalysisResult:
    target = FileTarget(path)
    orch = _build_orchestrator(stream)
    return orch.run(target, mode)


@app.command()
def scan(
    path: Path = typer.Argument(..., exists=True, readable=True, help="File to scan"),
    deep: bool = typer.Option(False, "--deep", help="Opt-in sandbox detonation (never local execution)"),
    tui: bool = typer.Option(False, "--tui", help="Interactive TUI mode (week 12)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Stream agent progress"),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Scan a file through the analysis pipeline."""
    if tui:
        try:
            from nullify.interfaces.cli.tui.app import NullifyTUI

            NullifyTUI().run()
        except ModuleNotFoundError as exc:
            err_console.print(f"[red]TUI requires the 'textual' extra:[/red] pip install 'nullify[tui]' ({exc})")
        return

    if json_out:
        logging.disable(logging.CRITICAL)
    res = _run_file_scan(path, ScanMode.DEEP if deep else ScanMode.STATIC_ONLY,
                         stream=verbose and not json_out)
    if json_out:
        console.print_json(res.to_json())
    else:
        _render_result(res)


@app.command("analyze-log")
def analyze_log(
    path: Path = typer.Argument(..., exists=True, readable=True, help="Sysmon JSONL / text log"),
    verbose: bool = typer.Option(False, "--verbose", "-v"),
    json_out: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    """Analyse a behavioural log for ATT&CK-mapped suspicious activity."""
    if json_out:
        logging.disable(logging.CRITICAL)
    orch = _build_orchestrator(stream=verbose and not json_out)
    res = orch.run(LogTarget(path), ScanMode.STATIC_ONLY)
    if json_out:
        console.print_json(res.to_json())
    else:
        _render_result(res)


@app.command()
def batch(
    directory: Path = typer.Argument(..., exists=True, file_okay=False, help="Directory of samples"),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write JSON report here"),
    deep: bool = typer.Option(False, "--deep", help="Opt-in sandbox detonation"),
) -> None:
    """Batch-scan a directory; optional JSON report for automation."""
    files = [p for p in sorted(directory.rglob("*")) if p.is_file()]
    if not files:
        err_console.print("[yellow]No files found in directory.[/yellow]")
        raise typer.Exit(1)

    mode = ScanMode.DEEP if deep else ScanMode.STATIC_ONLY
    results = []
    for i, path in enumerate(files, 1):
        console.print(f"[bold cyan][{i}/{len(files)}][/bold cyan] {path.name}")
        try:
            results.append(_run_file_scan(path, mode, stream=False).to_dict())
        except Exception as exc:  # noqa: BLE001 — batch must continue past bad files
            err_console.print(f"[red]error scanning {path}: {exc}[/red]")
            results.append({"path": str(path), "error": str(exc)})

    malicious = sum(1 for r in results if r.get("verdict") == "malicious")
    console.print(f"\n[bold]Scanned {len(results)} file(s): "
                  f"{malicious} malicious, "
                  f"{sum(1 for r in results if r.get('verdict') == 'suspicious')} suspicious, "
                  f"{sum(1 for r in results if r.get('verdict') == 'benign')} benign[/bold]")

    if output:
        report = {"generated_by": f"nullify {__version__}", "results": results}
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        console.print(f"Report written to [bold]{output}[/bold]")


if __name__ == "__main__":
    app()
