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
    menu_table.add_row(
        "[7]", "System PC Scan", "Audit PC drop locations, autostarts & persistence hotspots"
    )
    menu_table.add_row("[0]", "Exit", "Quit Nullify console")

    console.print(menu_table)
    console.print()

    try:
        choice = Prompt.ask(
            "[bold green]Select an action[/bold green]",
            choices=["1", "2", "3", "4", "5", "6", "7", "0", "q"],
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

        elif choice == "7":
            console.print("\n[bold]Select scan scope:[/bold]")
            console.print("  [1] Quick Scan (User Downloads/Desktop, /tmp, autostarts, cron, systemd)")
            console.print("  [2] Full PC Scan (All storage drives, excluding kernel pseudo-filesystems)")
            scope = Prompt.ask("Choose mode", choices=["1", "2"], default="1")
            system_scan(quick=(scope == "1"))


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


@app.command("system-scan")
def system_scan(
    quick: bool = typer.Option(
        True, "--quick/--full", help="Quick scan (drop & persistence hotspots) vs Full PC scan"
    ),
    output: Path | None = typer.Option(None, "--output", "-o", help="Write JSON report here"),
) -> None:
    """Scan the PC for threats and malicious persistence mechanisms."""
    import os
    from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

    console.print()
    console.print(Panel.fit(
        f"[bold cyan]NULLIFY SYSTEM THREAT SCAN // {'QUICK AUDIT' if quick else 'FULL PC SCAN'}[/bold cyan]\n"
        f"[dim]{'Auditing primary execution hotspots, autostarts, and persistence directories.' if quick else 'Auditing storage volumes (excluding virtual/kernel pseudo-filesystems).'}[/dim]",
        border_style="cyan"
    ))

    is_windows = os.name == "nt"
    home = Path.home()

    if is_windows:
        excluded_dirs = {
            "$Recycle.Bin", "System Volume Information", "WinSxS"
        }
        if quick:
            candidates = [
                home / "Downloads",
                home / "Desktop",
                Path(os.environ.get("TEMP", "C:\\Windows\\Temp")),
                Path(os.environ.get("APPDATA", "C:\\Users\\Default\\AppData\\Roaming")),
                Path(os.environ.get("LOCALAPPDATA", "C:\\Users\\Default\\AppData\\Local")),
                home / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup",
                Path("C:\\Windows\\Temp"),
                Path("C:\\ProgramData"),
            ]
            scan_paths = [p for p in candidates if p.exists() and p.is_dir()]
        else:
            sys_drive = os.environ.get("SystemDrive", "C:")
            scan_paths = [Path(f"{sys_drive}\\")]
    else:
        excluded_dirs = {
            "/proc", "/sys", "/dev", "/run", "/snap", "/var/lib/docker", "/var/lib/containerd",
            "/lost+found", "/tmp/.X11-unix", "/tmp/.ICE-unix"
        }
        if quick:
            candidates = [
                home / "Downloads",
                home / "Desktop",
                home / ".local" / "bin",
                home / ".config" / "autostart",
                home / ".config" / "systemd" / "user",
                Path("/tmp"),
                Path("/var/tmp"),
                Path("/dev/shm"),
                Path("/etc/cron.d"),
                Path("/etc/cron.daily"),
                Path("/etc/cron.hourly"),
                Path("/etc/systemd/system"),
                Path("/usr/local/bin"),
            ]
            scan_paths = [p for p in candidates if p.exists() and p.is_dir()]
        else:
            scan_paths = [Path("/")]

    files_to_scan: list[Path] = []
    console.print("[dim]Collecting target files...[/dim]")

    for root_dir in scan_paths:
        if quick:
            for p in root_dir.rglob("*"):
                try:
                    if p.is_file() and not p.is_symlink():
                        files_to_scan.append(p)
                except (PermissionError, OSError):
                    continue
        else:
            for dirpath, dirnames, filenames in os.walk(str(root_dir), followlinks=False):
                dirnames[:] = [
                    d for d in dirnames
                    if os.path.join(dirpath, d) not in excluded_dirs
                    and not any(os.path.join(dirpath, d).startswith(ex + "/") for ex in excluded_dirs)
                ]
                for fn in filenames:
                    fp = Path(dirpath) / fn
                    try:
                        if fp.is_file() and not fp.is_symlink():
                            files_to_scan.append(fp)
                    except (PermissionError, OSError):
                        continue

    if not files_to_scan:
        console.print("[yellow]No files found to scan.[/yellow]")
        return

    console.print(f"[bold]Identified [cyan]{len(files_to_scan)}[/cyan] target files to inspect.[/bold]\n")

    threats = []
    suspicious = []
    scanned_count = 0
    mode = ScanMode.STATIC_ONLY

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[cyan]Scanning...", total=len(files_to_scan))
        for p in files_to_scan:
            disp_name = p.name if len(p.name) <= 30 else p.name[:27] + "..."
            progress.update(task, description=f"[cyan]Scanning: [dim]{disp_name}[/dim]")
            try:
                res = _run_file_scan(p, mode, stream=False)
                scanned_count += 1
                if res.verdict == Verdict.MALICIOUS:
                    threats.append((p, res))
                elif res.verdict == Verdict.SUSPICIOUS:
                    suspicious.append((p, res))
            except Exception:
                pass
            progress.advance(task)

    console.print("\n[bold]Scan Complete.[/bold]")
    if threats:
        console.print(f"\n[bold red]CRITICAL: Found {len(threats)} MALICIOUS threat(s)![/bold red]")
        threat_table = Table(title="Detected Threats", header_style="bold red")
        threat_table.add_column("File", style="bold white")
        threat_table.add_column("Type", style="red")
        threat_table.add_column("Confidence", style="yellow")
        threat_table.add_column("Key Finding", style="dim")
        for tp, tr in threats:
            key_finding = tr.findings[0].title if tr.findings else "Malicious patterns"
            threat_table.add_row(str(tp), tr.malware_type or "unknown", f"{int(tr.confidence * 100)}%", key_finding)
        console.print(threat_table)
    elif suspicious:
        console.print(f"\n[bold yellow]Notice: Found {len(suspicious)} suspicious file(s).[/bold yellow]")
    else:
        console.print("\n[bold green]✓ Clean: No active malware or suspicious threats detected on this system.[/bold green]")

    if output:
        out_data = {
            "mode": "quick" if quick else "full",
            "scanned": scanned_count,
            "threats": [{"path": str(p), "verdict": r.verdict.value, "type": r.malware_type} for p, r in threats],
            "suspicious": [{"path": str(p), "verdict": r.verdict.value} for p, r in suspicious],
        }
        output.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
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
