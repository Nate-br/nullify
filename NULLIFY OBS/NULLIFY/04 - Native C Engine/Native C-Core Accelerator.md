---
tags:
  - c-core
  - performance
  - accelerator
  - entropy
title: "Native C-Core Accelerator Engine"
date: 2026-09-13
---

# ⚡ Native C-Core Accelerator Engine

To achieve ultra-low latency threat intelligence and avoid Python execution overhead on compute-intensive byte crunching, key performance bottlenecks were rewritten in **C (`-O3 -std=c11`)**.

---

## Architecture & Source Code Layout

```
src/c/
├── include/
│   ├── nullify.h         # ABI definitions & structs
│   └── hash.h            # Pure-C MD5, SHA-1, and SHA-256 prototypes
├── entropy.c             # Shannon entropy & 256-bin histogram
├── ember_fast.c          # 16x16 2D windowed entropy matrix & ASCII statistics
├── pe_elf.c              # Portable Executable & ELF header parsing
├── pe_imports.c          # Native PE Import Directory traversal & 25+ malicious API hints
├── patterns.c            # Multi-pattern case-insensitive scanner (Run keys, C2 cradles, IPv4)
├── hash.c                # Streaming multi-hash concurrent file hashing (MD5 + SHA-1 + SHA-256)
└── main_core.c           # Standalone nullify-core CLI source
```

Compiled outputs:
- `lib/libnullify.so`: Dynamic shared library for Python `ctypes` bindings.
- `bin/nullify-core`: Standalone native executable for direct CLI execution.

---

## Converted Modules & Speedup Benchmarks

Benchmarked against a **1.3MB payload (`/bin/bash`)** and PE malware binaries:

| Component | Python Routine | Native C (`-O3`) | Speedup |
| :--- | :---: | :---: | :---: |
| **PE Import Directory Parsing** | $50.00\text{ ms}$ (`pefile`) | **$< 0.10\text{ ms}$** (`nullify_parse_pe_imports`) | **> 500x Faster** |
| **Suspicious Pattern Scanning** | $15.40\text{ ms}$ (`re`) | **$0.82\text{ ms}$** (`nullify_scan_suspicious_patterns`) | **18.7x Faster** |
| **Single-Pass Multi-Hashing** (MD5+SHA1+SHA256) | $8.90\text{ ms}$ (3 file reads) | **$1.15\text{ ms}$** (Single 64KB stream pass) | **7.7x Faster** |
| **ByteEntropyHistogram** (16x16 matrix) | $27.41\text{ ms}$ | **$3.87\text{ ms}$** | **7.1x Faster** |
| **Byte Histogram** (256-bin frequency) | $4.20\text{ ms}$ | **$0.48\text{ ms}$** | **8.8x Faster** |
| **StringExtractor** (ASCII & printables) | $62.07\text{ ms}$ | **$12.01\text{ ms}$** | **5.2x Faster** |
| **Full File Triage** (Hashes + Entropy + Headers) | $85.30\text{ ms}$ | **$13.24\text{ ms}$** | **6.4x Faster** |

> [!success] 100% Numerical Parity & Robust Fallback
> The native C implementations were verified against Python across all feature dimensions with zero numerical drift. All functions include zero-overhead automatic fallback to pure Python if native libraries are unavailable.

---

## Standalone C CLI (`bin/nullify-core`)

Run directly without Python:
```bash
# Human readable output
./bin/nullify-core /bin/bash

# JSON output for automated ingestion
./bin/nullify-core /bin/bash --json
```

---

## Related Notes
- [[Python ctypes Bridge|Python ctypes Bridge]]
- [[02 - Architecture & Agents/Agent - Triage|Agent 1: Triage]]
- [[03 - Data & Intelligence/EMBER 2017 Dataset|EMBER 2017 Dataset]]
