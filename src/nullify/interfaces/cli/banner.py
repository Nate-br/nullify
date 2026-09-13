"""Nullify ASCII Art Banner for CLI."""

from __future__ import annotations

from rich.console import Console

BANNER_TEXT: str = """\
███╗   ██╗██╗   ██╗██╗     ██╗     ██╗███████╗██╗   ██╗
████╗  ██║██║   ██║██║     ██║     ██║██╔════╝╚██╗ ██╔╝
██╔██╗ ██║██║   ██║██║     ██║     ██║█████╗   ╚████╔╝ 
██║╚██╗██║██║   ██║██║     ██║     ██║██╔══╝    ╚██╔╝  
██║ ╚████║╚██████╔╝███████╗███████╗██║██║        ██║   
╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚══════╝╚═╝╚═╝        ╚═╝\
"""

# Backward compatibility aliases
FALLBACK_ASCII: str = BANNER_TEXT
BANNER_ANSI_LINES: list[str] = [BANNER_TEXT]


def print_banner(console: Console | None = None) -> None:
    """Print the clean block Nullify ASCII art banner."""
    c = console or Console()
    c.print(f"[bold cyan]{BANNER_TEXT}[/bold cyan]")
