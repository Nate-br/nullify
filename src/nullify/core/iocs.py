"""Offline IOC (indicator of compromise) hash intel.

Loads known-bad hashes from a local file — no network, no APIs. Used by the
triage agent to flag samples whose hash is already on a watch list.

File format (one hash per line):
    # comments start with '#'
    44d88612fea8a8f36de82e1278abb02f           # md5/sha1/sha256, bare or...
    e1112134b6dcc8bed54e0e34d8ac272795e73d74   # family=ej-tracon source=some-feed

Location: <repo>/iocs/hashes.txt by default, override with NULLIFY_IOC_FILE.
"""

from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_IOC_FILE = _REPO_ROOT / "iocs" / "hashes.txt"

_VALID_LENGTHS = {32, 40, 64}  # md5, sha1, sha256
_CACHE: dict[tuple[str, int], dict[str, str]] = {}


def ioc_file() -> Path:
    """Active IOC file path (env override wins)."""
    env = os.getenv("NULLIFY_IOC_FILE", "").strip()
    return Path(env) if env else DEFAULT_IOC_FILE


def load_hashes(path: Path | None = None, *, mtime: int | None = None) -> dict[str, str]:
    """Parse the watch list into {hash_lowercase: comment}.

    Returns {} when the file is missing. Malformed lines are skipped.
    Result is cached per (path, mtime) so scans don't re-read the file.
    """
    path = path or ioc_file()
    try:
        stat = path.stat()
    except OSError:
        return {}
    key = (str(path), mtime if mtime is not None else int(stat.st_mtime))
    if key in _CACHE:
        return _CACHE[key]

    out: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}
    for raw in lines:
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split(None, 1)
        h = parts[0].lower()
        if len(h) not in _VALID_LENGTHS or not all(c in "0123456789abcdef" for c in h):
            continue
        note = parts[1].strip() if len(parts) > 1 else ""
        out[h] = note  # last valid line wins for duplicate hashes
    _CACHE[key] = out
    return out


def lookup(sha256: str) -> dict[str, object] | None:
    """Return {'known_malicious': True, 'source': 'local-intel', ...} on a hit."""
    table = load_hashes()
    if not table:
        return None
    note = table.get(sha256.lower())
    if note is None:
        return None
    return {"known_malicious": True, "source": "local-intel", "note": note}
