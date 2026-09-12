"""Nullify command-line interface.

Commands:
    scan          analyse a file (static by default, --deep for opt-in sandbox)
    analyze-log   correlate a behavioural log (Sysmon JSONL, text)
    batch         scan every file in a directory, optional JSON report
    web           launch the local web console

Running `nullify` without arguments launches the interactive analysis console.
All commands call the shared Orchestrator — no analysis logic lives here (PLAN.md §4.3).
"""

from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
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
from nullify.interfaces.cli.banner import print_banner

app = typer.Typer(
    name="nullify",
    help="Agentic AI-powered malware & malware-type detection system.",
    no_args_is_help=False,
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


def interactive_menu() -> None:
    """Interactive CLI menu when nullify is run with no arguments."""
    print_banner(console)
    console.print()
    console.print(
        Panel(
            "[bold white]Nullify Interactive Threat Analysis Console[/bold white]\n"
            "[dim]Agentic Pipeline · XGBoost on EMBER (99.46% acc) · YARA Rules · MITRE ATT&CK[/dim]",
            border_style="blue",
            title=f"[bold cyan]v{__version__}[/bold cyan]",
            title_align="right",
        )
    )
    console.print()

    menu_table = Table(show_header=False, box=None, padding=(0, 2))
    menu_table.add_column("Key", style="bold cyan", no_wrap=True)
    menu_table.add_column("Action", style="bold white")
    menu_table.add_column("Description", style="dim")

    menu_table.add_row("[1]", "Quick Scan", "Standard static & ML inspection (fast, safe)")
    menu_table.add_row(
        "[2]", "Deep Detonation Scan", "Opt-in sandboxed detonation (--deep via CAPEv2)"
    )
    menu_table.add_row(
        "[3]", "Analyze Behavioral Log", "Correlate Sysmon JSONL or Windows EVTX logs"
    )
    menu_table.add_row("[4]", "Batch Scan Directory", "Scan an entire directory of binaries")
    menu_table.add_row(
        "[5]", "Launch Web Console", "Start local Framer dashboard at http://127.0.0.1:8000"
    )
    menu_table.add_row(
        "[6]", "Test Synthetic Demos", "Scan safe built-in fixtures (Trojan, Ransomware, etc.)"
    )
    menu_table.add_row("[0]", "Exit", "Quit Nullify console")

    console.print(menu_table)
    console.print()

    try:
        choice = Prompt.ask(
            "[bold green]Select an action[/bold green]",
            choices=["1", "2", "3", "4", "5", "6", "0", "q"],
            default="1",
        )
    except (KeyboardInterrupt, EOFError):
        console.print("\n[dim]Exiting Nullify.[/dim]")
        return

    if choice in ("0", "q"):
        console.print("[dim]Exiting Nullify. Stay secure![/dim]")
        return

    if choice == "1":
        path_str = Prompt.ask("\nEnter file path to scan")
        p = Path(path_str.strip().strip("'\""))
        if not p.is_file():
            err_console.print(f"[red]Error: File '{p}' not found or is not a file.[/red]")
            return
        console.print()
        res = _run_file_scan(p, ScanMode.STATIC_ONLY, stream=True)
        _render_result(res)

    elif choice == "2":
        path_str = Prompt.ask("\nEnter file path for deep sandbox scan")
        p = Path(path_str.strip().strip("'\""))
        if not p.is_file():
            err_console.print(f"[red]Error: File '{p}' not found.[/red]")
            return
        console.print()
        res = _run_file_scan(p, ScanMode.DEEP, stream=True)
        _render_result(res)

    elif choice == "3":
        log_str = Prompt.ask("\nEnter log path (Sysmon .jsonl / EVTX)")
        p = Path(log_str.strip().strip("'\""))
        if not p.is_file():
            err_console.print(f"[red]Error: Log file '{p}' not found.[/red]")
            return
        console.print()
        orch = _build_orchestrator(stream=True)
        res = orch.run(LogTarget(p), ScanMode.STATIC_ONLY)
        _render_result(res)

    elif choice == "4":
        dir_str = Prompt.ask("\nEnter directory path to batch scan")
        d = Path(dir_str.strip().strip("'\""))
        if not d.is_dir():
            err_console.print(f"[red]Error: Directory '{d}' not found.[/red]")
            return
        console.print()
        batch(directory=d, output=None, deep=False)

    elif choice == "5":
        console.print(
            "\n[bold cyan]Starting Nullify Web Console on [underline]http://127.0.0.1:8000[/underline]...[/bold cyan]"
        )
        console.print("[dim]Press Ctrl+C to stop the server.[/dim]\n")
        web_cmd(host="127.0.0.1", port=8000)

    elif choice == "6":
        console.print("\n[bold]Select a synthetic demo target:[/bold]")
        console.print("  [1] Trojan Dropper (CreateRemoteThread + WinExec + Run-key persistence)")
        console.print("  [2] Ransomware Sample (CryptEncrypt + CryptGenKey + Ransom note)")
        console.print("  [3] Clean Benign Application (Harmless PE, no malicious indicators)")
        console.print("  [4] Sysmon Behavioral Log (Temp directory execution, scheduled task)")
        s_choice = Prompt.ask("Choose sample", choices=["1", "2", "3", "4"], default="1")

        tmp_dir = Path(tempfile.gettempdir()) / "nullify_cli_demos"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        console.print()

        if s_choice == "1":
            p = tmp_dir / "demo_trojan.exe"
            blob = bytearray(b"MZ" + b"\x00" * 62)
            blob += (
                b"CreateRemoteThread\00WinExec\00URLDownloadToFile\00"
                b"Software\\Microsoft\\Windows\\CurrentVersion\\Run\x00"
            )
            blob += b"\x00" * 128
            p.write_bytes(bytes(blob))
            res = _run_file_scan(p, ScanMode.STATIC_ONLY, stream=True)
            _render_result(res)
        elif s_choice == "2":
            p = tmp_dir / "demo_ransomware.exe"
            blob = bytearray(b"MZ" + b"\x00" * 62)
            blob += (
                b"CryptEncrypt\00CryptGenKey\00FindFirstFile\00"
                b"README_FOR_DECRYPT.txt: your files have been encrypted\x00"
            )
            blob += b"\x00" * 128
            p.write_bytes(bytes(blob))
            res = _run_file_scan(p, ScanMode.STATIC_ONLY, stream=True)
            _render_result(res)
        elif s_choice == "3":
            p = tmp_dir / "demo_benign.exe"
            blob = bytearray(b"MZ" + b"\x00" * 62)
            blob += b"Nullify synthetic benign test application.\x00"
            p.write_bytes(bytes(blob))
            res = _run_file_scan(p, ScanMode.STATIC_ONLY, stream=True)
            _render_result(res)
        elif s_choice == "4":
            p = tmp_dir / "demo_sysmon.jsonl"
            lines = [
                '{"event": "Process Create", "image": "C:\\\\Windows\\\\system32\\\\cmd.exe"}',
                '{"event": "Process Create", "image": "C:\\\\Users\\\\pub\\\\AppData\\\\Temp\\\\dropper.exe"}',
                '{"event": "Process Create", "image": "C:\\\\Windows\\\\system32\\\\schtasks.exe /create /tn updater"}',
                '{"event": "Registry", "target": "HKCU\\\\Software\\\\Microsoft\\\\Windows\\\\CurrentVersion\\\\Run\\\\updater"}',
            ]
            p.write_text("\n".join(lines), encoding="utf-8")
            orch = _build_orchestrator(stream=True)
            res = orch.run(LogTarget(p), ScanMode.STATIC_ONLY)
            _render_result(res)


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context) -> None:
    """Agentic AI-powered malware & malware-type detection system."""
    if ctx.invoked_subcommand is None:
        interactive_menu()


@app.command()
def scan(
    path: Path = typer.Argument(..., exists=True, readable=True, help="File to scan"),
    deep: bool = typer.Option(
        False, "--deep", help="Opt-in sandbox detonation (never local execution)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Stream agent progress"),
    json_out: bool = typer.Option(False, "--json", help="Machine-readable JSON output"),
) -> None:
    """Scan a file through the analysis pipeline."""
    if json_out:
        logging.disable(logging.CRITICAL)
    elif verbose:
        print_banner(console)

    res = _run_file_scan(
        path,
        ScanMode.DEEP if deep else ScanMode.STATIC_ONLY,
        stream=verbose and not json_out,
    )
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
    elif verbose:
        print_banner(console)

    orch = _build_orchestrator(stream=verbose and not json_out)
    res = orch.run(LogTarget(path), ScanMode.STATIC_ONLY)
    if json_out:
        console.print_json(res.to_json())
    else:
        _render_result(res)


@app.command()
def batch(
    directory: Path = typer.Argument(
        ..., exists=True, file_okay=False, help="Directory of samples"
    ),
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
    console.print(
        f"\n[bold]Scanned {len(results)} file(s): "
        f"{malicious} malicious, "
        f"{sum(1 for r in results if r.get('verdict') == 'suspicious')} suspicious, "
        f"{sum(1 for r in results if r.get('verdict') == 'benign')} benign[/bold]"
    )

    if output:
        report = {"generated_by": f"nullify {__version__}", "results": results}
        output.write_text(json.dumps(report, indent=2), encoding="utf-8")
        console.print(f"Report written to [bold]{output}[/bold]")


@app.command("web")
def web_cmd(
    host: str = typer.Option("127.0.0.1", "--host", help="Host to bind to"),
    port: int = typer.Option(8000, "--port", help="Port to bind to"),
) -> None:
    """Launch the Web UI backend."""
    if host == "0.0.0.0":
        err_console.print("[red]Never bind to 0.0.0.0 for safety reasons. Use 127.0.0.1.[/red]")
        raise typer.Exit(1)

    try:
        import uvicorn

        uvicorn.run("nullify.interfaces.web.backend:app", host=host, port=port)
    except ModuleNotFoundError as exc:
        err_console.print(
            f"[red]Web UI requires the 'web' extra:[/red] pip install 'nullify[web]' ({exc})"
        )


if __name__ == "__main__":
    app()
