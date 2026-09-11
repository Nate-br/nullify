"""Rule generator — derive a YARA rule from a scan's findings.

Turns the observable evidence of a malicious scan (suspicious imports,
embedded strings) into a YARA rule. Works offline on anything Nullify can
already parse; no malware execution is involved.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

_IDENT_RE = re.compile(r"[^A-Za-z0-9_]")
_MAX_STRINGS = 12
_MIN_TOKEN_LEN = 5


def _safe_ident(name: str) -> str:
    ident = _IDENT_RE.sub("_", name).strip("_")
    return ident or "generated"


def _import_tokens(imports: list[str]) -> list[str]:
    """Pull API-looking identifiers out of raw import strings."""
    tokens: list[str] = []
    for imp in imports or []:
        for tok in re.findall(r"[A-Za-z][A-Za-z0-9_]{4,}", str(imp)):
            if tok.lower() in {
                "kernel32", "user32", "ntdll", "advapi32", "ws2_32",
                "wininet", "winhttp", "shell32", "ole32", "oleaut32",
            }:
                continue  # library names, not APIs
            tokens.append(tok)
    return tokens


def from_findings(findings: list[dict[str, Any]], imports: list[str],
                  family: str, name_hint: str = "") -> str:
    """Build a YARA rule string from a report's findings + imports."""
    seen: set[str] = set()
    strings: list[str] = []

    def add(token: str) -> None:
        if len(strings) >= _MAX_STRINGS:
            return
        tok = token.strip()
        if len(tok) < _MIN_TOKEN_LEN or tok.lower() in seen:
            return
        seen.add(tok.lower())
        strings.append(tok)

    for tok in _import_tokens(imports):
        add(tok)
    for f in findings or []:
        blob = " ".join(str(f.get(k, "")) for k in ("title", "detail"))
        for tok in re.findall(r"[A-Za-z][A-Za-z0-9_]{4,}", blob):
            add(tok)

    ident = _safe_ident(family)
    hint = _safe_ident(name_hint) if name_hint else "generated"
    rule_name = f"Gen_{ident}_{hint[:24]}_{hashlib.sha1(ident.encode()).hexdigest()[:6]}"

    lines = [
        f"rule {rule_name} {{",
        "    meta:",
        f'        description = "Auto-generated from a Nullify scan (family: {family})"',
        '        severity = "HIGH"',
        '        malware_type = ' + f'"{family.lower()}"',
        "    strings:",
    ]
    for i, tok in enumerate(strings):
        lines.append(f'        $s{i} = "{tok}" ascii wide')
    if not strings:
        lines.append('        $empty = "nullify-no-evidence" ascii wide')
    cond = " or ".join(f"$s{i}" for i in range(min(len(strings), 1) or 1))
    if strings:
        cond = " or ".join(f"$s{i}" for i in range(len(strings)) if i < 3) or "$s0"
    lines += [
        "    condition:",
        f"        uint16(0) == 0x5a4d and ({cond})",
        "}",
    ]
    return "\n".join(lines) + "\n"
