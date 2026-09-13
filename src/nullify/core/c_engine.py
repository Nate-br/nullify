"""C-Core Accelerator Bridge for Nullify.

Provides high-performance native C bindings for compute-heavy components:
- Fast Shannon entropy computation
- EMBER 2017 v2 sliding-window byte entropy matrix (16x16)
- EMBER 2017 v2 ASCII string scanning & printable distribution
- Native PE & ELF header triage & hash computation

If `libnullify.so` is not found or fails to load, functions gracefully fallback
to pure Python implementations.
"""

from __future__ import annotations

import ctypes
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

# Resolve repo root and library path
_CORE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _CORE_DIR.parent.parent.parent
_LIB_PATH = _REPO_ROOT / "lib" / "libnullify.so"


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
        "sha256": res.sha256.decode("utf-8", "ignore"),
    }
