---
tags:
  - python
  - ctypes
  - bridge
  - fallback
title: "Python ctypes Bridge & Graceful Fallback"
date: 2026-09-13
---

# 🌉 Python ctypes Bridge & Graceful Fallback

The Python bridge is implemented in `src/nullify/core/c_engine.py`. It allows the high-level Python application (FastAPI and Typer CLI) to access the raw speed of native C without requiring manual compilation steps from the user.

---

## How It Works

1. **Auto-Discovery & Auto-Build**:
   - Tries loading `lib/libnullify.so`.
   - If missing, it checks if `Makefile` and a C compiler (`gcc`) exist, then automatically executes `make lib/libnullify.so` in the background.
2. **Type-Safe Signatures**:
   - Maps C structures (`nullify_triage_result_t`, `nullify_string_stats_t`) into `ctypes.Structure` classes.
3. **Graceful Degradation**:
   - If the shared library fails to load or cannot be compiled, `is_c_accelerated()` returns `False` and the functions transparently fall back to pure-Python implementations.

---

## Function Mappings

```python
from nullify.core.c_engine import (
    is_c_accelerated,
    fast_entropy,
    fast_byte_entropy_histogram,
    fast_extract_strings,
    fast_triage_file,
)
```

- `fast_entropy(bytes) -> float`: Native Shannon entropy computation.
- `fast_byte_entropy_histogram(bytes, step, window) -> list[int]`: 256-element 2D matrix.
- `fast_extract_strings(bytes) -> dict`: Single-pass ASCII string statistics.
- `fast_triage_file(path) -> dict`: Full triage metadata extraction.

---

## Related Notes
- [[Native C-Core Accelerator|Native C-Core Accelerator]]
- [[02 - Architecture & Agents/Agent - Triage|Agent 1: Triage]]
- [[03 - Data & Intelligence/EMBER 2017 Dataset|EMBER 2017 Dataset]]
