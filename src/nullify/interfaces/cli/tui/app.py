"""Textual TUI app — week 12 milestone stub.

Consumes the same EventBus stream as the CLI; until implemented, `nullify scan
--tui` prints a pointer to the CLI. Keep this interface so the CLI doesn't change
when the TUI lands.
"""

from __future__ import annotations


class NullifyTUI:
    """Placeholder that raises ModuleNotFoundError to trigger the CLI fallback."""

    def __init__(self) -> None:
        raise ModuleNotFoundError(
            "TUI lands in week 12. Until then use plain CLI output "
            "(drop --tui) or install the 'textual' extra."
        )

    def run(self) -> None:  # pragma: no cover — never reached
        raise NotImplementedError
