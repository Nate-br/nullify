"""C-Core Accelerator Bridge for Nullify.

Provides high-performance native C bindings for compute-heavy components:
- Fast Shannon entropy computation
- Native byte frequency histogram
- EMBER 2017 v2 sliding-window byte entropy matrix (16x16)
- EMBER 2017 v2 ASCII string scanning & printable distribution
- Native PE & ELF header triage & hash computation (MD5, SHA1, SHA256)
- Native PE import table directory parser & malicious capability classifier
- Native multi-pattern string and drop path scanner

If `libnullify.so` is not found or fails to load, functions gracefully fallback
to pure Python implementations.
"""

from __future__ import annotations

import ctypes
import hashlib
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# Resolve repo root and library path
_CORE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _CORE_DIR.parent.parent.parent
_LIB_NAME = "nullify.dll" if sys.platform == "win32" else "libnullify.so"
_LIB_PATH = _REPO_ROOT / "lib" / _LIB_NAME


class _NullifyTriageResult(ctypes.Structure):
    _fields_ = [
        ("size_bytes", ctypes.c_uint64),
        ("entropy", ctypes.c_double),
        ("magic", ctypes.c_int32),
        ("architecture", ctypes.c_char * 32),
        ("is_executable", ctypes.c_int32),
        ("is_packed", ctypes.c_int32),
        ("num_sections", ctypes.c_int32),
        ("entry_section", ctypes.c_char * 32),
        ("md5", ctypes.c_char * 33),
        ("sha1", ctypes.c_char * 41),
        ("sha256", ctypes.c_char * 65),
    ]


class _NullifyStringStats(ctypes.Structure):
    _fields_ = [
        ("count", ctypes.c_uint32),
        ("avg_length", ctypes.c_double),
        ("char_counts", ctypes.c_uint32 * 96),
        ("char_entropy", ctypes.c_double),
        ("num_paths", ctypes.c_uint32),
        ("num_urls", ctypes.c_uint32),
        ("num_registry", ctypes.c_uint32),
        ("num_mz", ctypes.c_uint32),
    ]


class _NullifyPeImportsResult(ctypes.Structure):
    _fields_ = [
        ("total_imports", ctypes.c_uint32),
        ("total_libraries", ctypes.c_uint32),
        ("libraries", (ctypes.c_char * 64) * 32),
        ("trojan_hits", ctypes.c_uint32),
        ("spyware_hits", ctypes.c_uint32),
        ("ransomware_hits", ctypes.c_uint32),
        ("worm_hits", ctypes.c_uint32),
        ("rootkit_hits", ctypes.c_uint32),
        ("matched_apis", (ctypes.c_char * 64) * 64),
        ("matched_families", (ctypes.c_char * 16) * 64),
        ("matched_count", ctypes.c_uint32),
    ]


class _NullifyPatternMatches(ctypes.Structure):
    _fields_ = [
        ("has_registry_run", ctypes.c_uint32),
        ("has_scheduled_task", ctypes.c_uint32),
        ("has_powershell_cradle", ctypes.c_uint32),
        ("has_hardcoded_ip", ctypes.c_uint32),
        ("has_drop_path", ctypes.c_uint32),
        ("has_ransom_note", ctypes.c_uint32),
        ("match_snippets", (ctypes.c_char * 128) * 6),
    ]


_LIB: ctypes.CDLL | None = None


def _load_c_lib() -> ctypes.CDLL | None:
    global _LIB
    if _LIB is not None:
        return _LIB

    # Try existing compiled library
    if _LIB_PATH.exists():
        try:
            _LIB = ctypes.CDLL(str(_LIB_PATH))
            _setup_signatures(_LIB)
            return _LIB
        except OSError:
            pass

    # Try building automatically if Makefile and gcc exist
    makefile = _REPO_ROOT / "Makefile"
    if makefile.exists():
        try:
            subprocess.run(
                ["make", "-C", str(_REPO_ROOT), "lib/libnullify.so"],
                check=True,
                capture_output=True,
                timeout=10,
            )
            if _LIB_PATH.exists():
                _LIB = ctypes.CDLL(str(_LIB_PATH))
                _setup_signatures(_LIB)
                return _LIB
        except Exception:
            pass

    # Try system loader fallback (e.g. libnullify.so in LD_LIBRARY_PATH)
    try:
        _LIB = ctypes.CDLL("libnullify.so")
        _setup_signatures(_LIB)
        return _LIB
    except OSError:
        pass

    return None


def _setup_signatures(lib: ctypes.CDLL) -> None:
    lib.nullify_entropy.argtypes = [ctypes.POINTER(ctypes.c_uint8), ctypes.c_size_t]
    lib.nullify_entropy.restype = ctypes.c_double

    lib.nullify_byte_histogram.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_uint32 * 256),
    ]
    lib.nullify_byte_histogram.restype = None

    lib.nullify_byte_entropy_histogram.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.c_size_t,
        ctypes.c_size_t,
        ctypes.c_size_t,
        ctypes.POINTER(ctypes.c_int64 * 256),
    ]
    lib.nullify_byte_entropy_histogram.restype = None

    lib.nullify_extract_strings.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.c_size_t,
        ctypes.POINTER(_NullifyStringStats),
    ]
    lib.nullify_extract_strings.restype = None

    lib.nullify_triage_buffer.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.c_size_t,
        ctypes.POINTER(_NullifyTriageResult),
    ]
    lib.nullify_triage_buffer.restype = ctypes.c_int

    lib.nullify_triage_file.argtypes = [
        ctypes.c_char_p,
        ctypes.POINTER(_NullifyTriageResult),
    ]
    lib.nullify_triage_file.restype = ctypes.c_int

    lib.nullify_hashes_file.argtypes = [
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
    ]
    lib.nullify_hashes_file.restype = ctypes.c_int

    lib.nullify_parse_pe_imports.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.c_size_t,
        ctypes.POINTER(_NullifyPeImportsResult),
    ]
    lib.nullify_parse_pe_imports.restype = ctypes.c_int

    lib.nullify_scan_suspicious_patterns.argtypes = [
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.c_size_t,
        ctypes.POINTER(_NullifyPatternMatches),
    ]
    lib.nullify_scan_suspicious_patterns.restype = ctypes.c_int


# Initialize library
_load_c_lib()


def is_c_accelerated() -> bool:
    """Return True if native C accelerator library is active."""
    return _LIB is not None


def fast_entropy(data: bytes) -> float:
    """Compute Shannon entropy using C accelerator if available, else pure Python."""
    if not data:
        return 0.0

    if _LIB is not None:
        buf = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
        return float(_LIB.nullify_entropy(buf, len(data)))

    # Pure Python fallback
    import collections
    counts = collections.Counter(data)
    total = len(data)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def fast_byte_histogram(data: bytes) -> list[int]:
    """Compute 256-bin byte frequency histogram using C accelerator."""
    if not data:
        return [0] * 256

    if _LIB is not None:
        buf = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
        out_hist = (ctypes.c_uint32 * 256)()
        _LIB.nullify_byte_histogram(buf, len(data), ctypes.byref(out_hist))
        return list(out_hist)

    # Pure Python fallback
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    return counts


def fast_byte_entropy_histogram(
    data: bytes, step: int = 1024, window: int = 2048
) -> list[int] | None:
    """Compute EMBER 16x16 2D Byte Entropy Histogram matrix via C-core.

    Returns 256-element list of int64, or None if C-core is unavailable.
    """
    if _LIB is None or not data:
        return None

    buf = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
    matrix = (ctypes.c_int64 * 256)()
    _LIB.nullify_byte_entropy_histogram(buf, len(data), step, window, ctypes.byref(matrix))
    return list(matrix)


def fast_extract_strings(data: bytes) -> dict[str, Any] | None:
    """Extract EMBER ASCII string features via single-pass C-core.

    Returns dict matching EMBER StringExtractor schema, or None if unavailable.
    """
    if _LIB is None or not data:
        return None

    buf = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
    stats = _NullifyStringStats()
    _LIB.nullify_extract_strings(buf, len(data), ctypes.byref(stats))

    char_counts = list(stats.char_counts)
    printables = sum(char_counts)

    return {
        "numstrings": int(stats.count),
        "avlength": float(stats.avg_length),
        "printabledist": char_counts,
        "printables": int(printables),
        "entropy": float(stats.char_entropy),
        "paths": int(stats.num_paths),
        "urls": int(stats.num_urls),
        "registry": int(stats.num_registry),
        "MZ": int(stats.num_mz),
    }


def fast_triage_file(path: str | Path) -> dict[str, Any] | None:
    """Triage file directly with C-core parser, hashes, and entropy."""
    if _LIB is None:
        return None

    c_path = str(path).encode("utf-8")
    res = _NullifyTriageResult()
    rc = _LIB.nullify_triage_file(c_path, ctypes.byref(res))
    if rc != 0:
        return None

    magic_map = {0: "unknown", 1: "pe", 2: "elf", 3: "script"}

    return {
        "size_bytes": int(res.size_bytes),
        "entropy": float(res.entropy),
        "magic": magic_map.get(int(res.magic), "unknown"),
        "architecture": res.architecture.decode("utf-8", "ignore"),
        "is_executable": bool(res.is_executable),
        "is_packed": bool(res.is_packed),
        "num_sections": int(res.num_sections),
        "entry_section": res.entry_section.decode("utf-8", "ignore"),
        "md5": res.md5.decode("utf-8", "ignore"),
        "sha1": res.sha1.decode("utf-8", "ignore"),
        "sha256": res.sha256.decode("utf-8", "ignore"),
    }


def fast_hashes_file(path: str | Path) -> dict[str, str]:
    """Compute MD5, SHA1, and SHA256 in a single native C streaming pass."""
    if _LIB is not None:
        c_path = str(path).encode("utf-8")
        md5_buf = ctypes.create_string_buffer(33)
        sha1_buf = ctypes.create_string_buffer(41)
        sha256_buf = ctypes.create_string_buffer(65)
        rc = _LIB.nullify_hashes_file(c_path, md5_buf, sha1_buf, sha256_buf)
        if rc == 0:
            return {
                "md5": md5_buf.value.decode("utf-8"),
                "sha1": sha1_buf.value.decode("utf-8"),
                "sha256": sha256_buf.value.decode("utf-8"),
            }

    # Python fallback
    md5, sha1, sha256 = hashlib.md5(), hashlib.sha1(), hashlib.sha256()
    with Path(path).open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            for h in (md5, sha1, sha256):
                h.update(chunk)
    return {
        "md5": md5.hexdigest(),
        "sha1": sha1.hexdigest(),
        "sha256": sha256.hexdigest(),
    }


def fast_parse_pe_imports(data: bytes) -> dict[str, Any] | None:
    """Extract PE imported libraries and match malicious capabilities in native C."""
    if _LIB is None or not data:
        return None

    buf = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
    res = _NullifyPeImportsResult()
    rc = _LIB.nullify_parse_pe_imports(buf, len(data), ctypes.byref(res))
    if rc != 0:
        return None

    libraries = [res.libraries[i].value.decode("utf-8", "ignore") for i in range(res.total_libraries)]
    matched_apis = []
    for i in range(res.matched_count):
        api = res.matched_apis[i].value.decode("utf-8", "ignore")
        fam = res.matched_families[i].value.decode("utf-8", "ignore")
        if api:
            matched_apis.append((api, fam))

    return {
        "total_imports": int(res.total_imports),
        "total_libraries": int(res.total_libraries),
        "libraries": libraries,
        "type_votes": {
            "trojan": int(res.trojan_hits),
            "spyware": int(res.spyware_hits),
            "ransomware": int(res.ransomware_hits),
            "worm": int(res.worm_hits),
            "rootkit": int(res.rootkit_hits),
        },
        "matched_apis": matched_apis,
    }


def fast_scan_patterns(data: bytes) -> dict[str, Any] | None:
    """Scan raw buffer for suspicious drops, registry keys, and beacons in native C."""
    if _LIB is None or not data:
        return None

    buf = (ctypes.c_uint8 * len(data)).from_buffer_copy(data)
    res = _NullifyPatternMatches()
    rc = _LIB.nullify_scan_suspicious_patterns(buf, len(data), ctypes.byref(res))
    if rc != 0:
        return None

    matches = []
    if res.has_registry_run:
        matches.append(("Registry Run-key persistence", res.match_snippets[0].value.decode("utf-8", "ignore"), "HIGH"))
    if res.has_scheduled_task:
        matches.append(("Scheduled task creation", res.match_snippets[1].value.decode("utf-8", "ignore"), "MEDIUM"))
    if res.has_powershell_cradle:
        matches.append(("PowerShell download cradle", res.match_snippets[2].value.decode("utf-8", "ignore"), "HIGH"))
    if res.has_hardcoded_ip:
        matches.append(("Hardcoded public IP address", res.match_snippets[3].value.decode("utf-8", "ignore"), "MEDIUM"))
    if res.has_drop_path:
        matches.append(("Executable drop path", res.match_snippets[4].value.decode("utf-8", "ignore"), "MEDIUM"))
    if res.has_ransom_note:
        matches.append(("Ransom note string", res.match_snippets[5].value.decode("utf-8", "ignore"), "CRITICAL"))

    return {"matches": matches}
