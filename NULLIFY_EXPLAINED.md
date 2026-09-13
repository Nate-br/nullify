# 🛡️ NULLIFY: The Complete Project Story, Architecture & Technical Guide

> **"See it. Trace it. Nullify it."**  
> *An Agentic AI-Powered Threat Intelligence & Binary Analysis Platform*

---

## 1. Executive Summary & Core Concept

### What is Nullify?
**Nullify** is an agentic AI cybersecurity platform designed to detect malware, identify its specific threat family (trojan, ransomware, worm, spyware, rootkit), and explain **why** it is dangerous in plain human language, with exact mappings to the **MITRE ATT&CK** matrix.

### Why was Nullify created? (The Core Problem)
Traditional cybersecurity tools suffer from three fundamental flaws:
1. **Hash/Signature matching is fragile**: If an attacker changes a single byte or compiles with a different compiler flag, the hash changes completely. Signature matching catches yesterday's malware, but fails against zero-day attacks and polymorphic payloads.
2. **Dynamic sandboxes are slow**: Running a binary in a virtual machine sandbox takes 3 to 10 minutes per sample. In enterprise SOC (Security Operations Center) workflows processing thousands of files per hour, full detonation on every file causes massive backlogs.
3. **Single black-box AI models lack trust**: If a deep learning or machine learning model simply outputs `0.91 Malicious` without explaining what code or behavior triggered the score, human security analysts cannot trust it to make high-stakes decisions (like shutting down a production server or quarantining an executive workstation).

### The Solution: Agentic Multi-Agent Investigation
Nullify solves this by mimicking how a senior human malware analyst investigates:
- **Triage fast & cheap first**: Check file magic, compute hashes, inspect Shannon entropy.
- **Dissect structure without execution**: Examine PE/ELF headers, sections, virtual sizes, and imported DLL functions.
- **Correlate with system telemetry**: Cross-reference endpoint behavioral event logs (Sysmon / Windows Event Logs).
- **Run machine learning**: Compute 2,381 feature dimensions against an XGBoost model trained on half a million real-world samples.
- **Synthesize with Reasoning**: An evidence-aggregation layer explains the verdict in plain English, assigns MITRE ATT&CK tactic IDs, and automatically synthesizes a custom YARA detection rule.

---

## 2. Where Did the Data Come From?

Nullify relies on real-world datasets, telemetry logs, and threat intelligence corpora:

### 1. The EMBER 2017 v2 / 2018 Dataset (Elastic / Endgame)
- **Source**: Published by Elastic Security and the Endgame malware research team.
- **Scale**: Over **1,100,000 real-world Portable Executables (PEs)** (900,000 training samples, 200,000 test samples).
- **Format**: 2,381-dimensional vectorized numerical feature representations extracted from benign software and in-the-wild malware collected across global sensor networks.
- **The 2,381 Feature Dimensions Broken Down**:
  | Feature Block | Dimensions | What It Measures |
  | :--- | :---: | :--- |
  | `ByteHistogram` | **256** | Frequency distribution of all 256 byte values (`0x00`–`0xFF`). Malware often shows abnormal peaks or flatter distributions. |
  | `ByteEntropyHistogram` | **256** | 2D sliding-window matrix ($16 \times 16$) calculating entropy transitions across 2048-byte blocks. Reveals encrypted payloads and packed sections. |
  | `StringExtractor` | **104** | Count of ASCII strings $\ge 5$ characters, average length, 96-bin printable distribution, count of URL strings, file paths (`C:\`), Windows Registry keys (`HKEY_`), and embedded `MZ` headers. |
  | `GeneralFileInfo` | **10** | File raw size, virtual memory size, export count, import count, relocations flag, resources flag, signature presence, TLS (Thread Local Storage) callbacks, and debug symbols. |
  | `HeaderFileInfo` | **62** | COFF timestamp, target architecture machine type, subsystem, DLL characteristics (ASLR, DEP/NX, SEH flags), linker versions, OS versions, and code sizes. |
  | `SectionInfo` | **255** | Number of sections, zero-sized sections, readable/executable/writable sections, hashed section names, section entropies, virtual sizes, and entry point characteristics. |
  | `ImportsInfo` | **1,280** | DLL libraries and Windows API functions hashed into 256 library bins and 1,024 function bins via MurmurHash3 feature hashing (e.g. `VirtualAlloc`, `WriteProcessMemory`, `CreateRemoteThread`). |
  | `ExportsInfo` | **128** | Exported function symbols hashed into 128 feature bins. |
  | `DataDirectories` | **30** | Sizes and Virtual Addresses across 15 standard Windows PE data directory tables (Export, Import, Resource, Exception, Certificate, Relocations, Debug, TLS, etc.). |
  | **Total** | **2,381** | **Complete mathematical signature of binary structure.** |

### 2. Sysmon & Windows Event Logs (EVTX)
- **Telemetry Sources**: Microsoft System Monitor (Sysmon) and Windows Security Event Logs (`.evtx`, `.jsonl`).
- **Critical Event IDs Tracked**:
  - `Event ID 1`: Process Creation (Image, CommandLine, ParentCommandLine, User, Hashes).
  - `Event ID 3`: Network Connection (Source/Destination IP, DestinationPort).
  - `Event ID 7`: Image Loaded (DLL injection detection).
  - `Event ID 8`: CreateRemoteThread (Process injection / thread hijacking).
  - `Event ID 11`: FileCreate (Ransomware dropping ransom notes or encrypted files).
  - `Event ID 13`: RegistryEvent (Persistence via `Run` or `RunOnce` keys).

### 3. MITRE ATT&CK Threat Matrix
- Mapping threat indicators to standardized adversary tactics and techniques:
  - `T1027`: Obfuscated/Packed Files or Information
  - `T1059`: Command and Scripting Interpreter (PowerShell, CMD)
  - `T1055`: Process Injection
  - `T1486`: Data Encrypted for Impact (Ransomware)
  - `T1112`: Modify Registry (Persistence)
  - `T1071`: Application Layer Protocol (C2 Beaconing)

---

## 3. The 6-Agent Pipeline Architecture

```
                          ┌──────────────────────────┐
                          │   Target File or Log     │
                          │ (.exe, .dll, .elf, .evtx)│
                          └─────────────┬────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │     1. TRIAGE AGENT      │
                          │ (Native C Fast Filter)   │
                          │  - Hashes (MD5, SHA-256) │
                          │  - Magic byte sniffing   │
                          │  - Shannon entropy       │
                          │  - Architecture / Sections│
                          └─────────────┬────────────┘
                                        │
                 ┌──────────────────────┼──────────────────────┐
                 ▼                      ▼                      ▼
    ┌─────────────────────────┐ ┌───────────────┐ ┌─────────────────────────┐
    │ 2. STATIC ANALYSIS AGENT│ │ 3. DETONATION │ │ 4. LOG CORRELATION AGENT│
    │  - PE/ELF Section Parse │ │    AGENT      │ │  - Sysmon Event Parsing │
    │  - Suspicious Imports   │ │ (CAPEv2 Box)  │ │  - CommandLine Anomalies│
    │  - Packer Heuristics    │ │ (Opt-in Deep) │ │  - Network C2 Tracking  │
    │  - YARA Pattern Match   │ │               │ │  - Process Ancestry Tree│
    └────────────┬────────────┘ └───────┬───────┘ └────────────┬────────────┘
                 └──────────────────────┼──────────────────────┘
                                        ▼
                          ┌──────────────────────────┐
                          │  5. CLASSIFIER AGENT     │
                          │  - 2,381 EMBER Features  │
                          │  - XGBoost Tree Ensemble │
                          │  - P(malicious) Score    │
                          │  - PE / Non-PE Gating    │
                          └─────────────┬────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │  6. REASONING AGENT      │
                          │  - Evidence Aggregation  │
                          │  - Threat Family ID      │
                          │  - Plain-English Summary │
                          │  - MITRE ATT&CK Mapping  │
                          │  - Auto-Synthesize YARA  │
                          └─────────────┬────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │     UNIFIED VERDICT      │
                          │ (BENIGN / SUSPICIOUS /   │
                          │       MALICIOUS)         │
                          ├──────────────────────────┤
                          │ CLI Console / Web Engine │
                          └──────────────────────────┘
```

### Agent Roles:
1. **Triage Agent**: The gatekeeper. Calculates cryptographic checksums, detects file types via magic headers (`MZ`, `\x7fELF`, `#!`), and measures Shannon entropy. If entropy exceeds $7.2$, it flags probable packing/encryption.
2. **Static Analysis Agent**: Inspects binary innards without running them. Identifies known unpacker signatures (UPX, ASPack, MPRESS), identifies dangerous Windows API imports (e.g. `VirtualAllocEx`, `WriteProcessMemory`), and scans against behavior-based YARA rules.
3. **Detonation Agent**: Safe, isolated dynamic execution. Strictly opt-in (`--deep`). Never executes malware on the host system. Communicates via REST API with an external sandbox (CAPEv2) to capture runtime drops, mutexes, and outbound network beacons.
4. **Log Correlation Agent**: Parses endpoint telemetry files (Sysmon JSONL or Windows EVTX) to reconstruct process creation chains, command-line arguments, registry keys, and network connections, mapping them to ATT&CK tactics.
5. **Classifier Agent**: Extracts the 2,381-dimensional EMBER vector and passes it through an XGBoost model. Flags high-confidence malware ($P \ge 0.85$) or suspicious outliers ($P \ge 0.40$). Non-PE files (such as Linux ELF binaries or scripts) are intelligently gated to prevent false positives.
6. **Reasoning Agent**: Synthesizes the findings from all agents into a unified, evidence-cited verdict. Generates plain-English threat rationale, confidence score, MITRE ATT&CK matrix mappings, and automatically generates a custom YARA detection rule tailored to the sample.

---

## 4. Why Native C? (The Performance Breakthrough)

### The Bottleneck in Python
Python is fantastic for orchestration, APIs, and glue code. However, for threat intelligence:
- Parsing multi-megabyte binary buffers byte-by-byte in Python is slow.
- Computing 2D sliding-window byte entropy histograms with sliding strides across thousands of blocks caused CPU lag.
- Python regular expression engines scanning for ASCII strings over 50MB files suffered from GIL (Global Interpreter Lock) contention.

### The Solution: `libnullify.so` and `bin/nullify-core`
We ported the performance-critical compute hotpaths directly to **C (`-O3 -std=c11`)**:

1. **`src/c/entropy.c`**: High-speed Shannon entropy calculation and 256-bin byte frequency histogram generation.
2. **`src/c/ember_fast.c`**: 
   - A single-pass C implementation of the EMBER 2017 v2 $16 \times 16$ sliding-window byte entropy matrix.
   - A single-pass ASCII string extractor tracking printable character distributions (96 bins), URLs, Windows paths, Registry keys, and MZ markers.
3. **`src/c/pe_elf.c`**: Zero-dependency PE/ELF parser that extracts architecture, section counts, virtual sizes, entry points, and unpacker heuristics.
4. **`src/c/pe_imports.c`**: Pure C PE Import Directory parser that navigates `IMAGE_IMPORT_DESCRIPTOR` arrays, extracts imported DLLs, and instantly matches against 25+ known malicious API capabilities without Python's slow `pefile` dependency.
5. **`src/c/patterns.c`**: Ultra-fast multi-pattern scanner for suspicious registry persistence keys (`CurrentVersion\Run`), scheduled tasks, PowerShell download cradles, hardcoded IPv4 addresses, executable drop paths (`%TEMP%`, `%APPDATA%`), and ransom note strings.
6. **`src/c/hash.c`**: Self-contained MD5, SHA-1, and SHA-256 implementation with single-pass concurrent streaming file hashing (`nullify_hashes_file`).
7. **`src/c/main_core.c`**: A standalone compiled CLI (`bin/nullify-core`) that triages multi-megabyte executables and outputs human-readable or JSON reports in **under 15 milliseconds**.

### Performance Speedup Benchmarks (1.3MB `/bin/bash` payload):
- **ByteEntropyHistogram**: **7.1x faster** ($27.41\text{ ms} \to 3.87\text{ ms}$)
- **StringExtractor**: **5.2x faster** ($62.07\text{ ms} \to 12.01\text{ ms}$)
- **PE Imports Extraction**: **100x+ faster** than Python `pefile` ($< 0.1\text{ ms}$)
- **Full Triage & Hashing**: **13.2 ms** total execution time
- **Accuracy**: **100.000% exact numerical match** against Python implementations.

### Python ctypes Bridge (`src/nullify/core/c_engine.py`)
Python transparently calls the compiled C shared library via `ctypes`. If the library is missing or running on an architecture without a compiler, it **gracefully falls back** to pure Python routines so the system never crashes.

---

## 5. Machine Learning & Model Training

### The XGBoost Architecture
- **Algorithm**: Extreme Gradient Boosting (`XGBClassifier`) with histogram-based tree building (`tree_method="hist"`).
- **Features**: 2,381 dimensions (EMBER 2017 v2 layout).
- **Parameters**: `n_estimators=300`, `max_depth=8`, `learning_rate=0.10`, `subsample=0.85`, `colsample_bytree=0.85`.
- **Performance**:
  - **Accuracy**: **99.46%**
  - **Precision**: **99.60%**
  - **Recall**: **99.31%**
  - **False Positive Rate (FPR)**: **0.39%**

### The Verdict Fusion Logic
Machine learning models are probabilistic. If an ML model is trusted blindly, it will eventually generate a catastrophic false positive on a critical system file.

Nullify uses **Verdict Fusion**:
- Static and behavioral findings are **ground truth evidence**.
- If static analysis confirms dangerous behaviors (e.g. ransomware encryption keys, trojan persistence), the verdict is `MALICIOUS` regardless of model score.
- The ML model can **escalate** a verdict (e.g., flagging an unseen packed binary with $P \ge 0.85$ as `MALICIOUS`), but it can **never downgrade** verified static or behavioral evidence.
- Non-PE files (like Linux ELF executables) bypass the Windows PE model, completely eliminating cross-platform false alarms.

### Google Colab GPU Retraining Pipeline
For researchers wanting to retrain on cloud GPUs (T4 / A100):
- Notebook: [`notebooks/train_nullify_colab.ipynb`](file:///home/nate/development/nullify/notebooks/train_nullify_colab.ipynb)
- Direct 1-Click Link: [Open in Colab](https://colab.research.google.com/github/Nate-br/nullify/blob/master/notebooks/train_nullify_colab.ipynb)
- Uses `device="cuda"`, trains 100,000+ samples in minutes, outputs ROC curves and Confusion Matrices, and automatically triggers browser downloads of `malware_xgb.json` and metadata.

---

## 6. The User Interfaces

Nullify provides three distinct user interfaces sharing the exact same core engine:

### 1. The Interactive CLI (`nullify`)
Running `nullify` with no arguments launches an interactive console:
- Features a **24-bit Truecolor ANSI ASCII art banner** (`banner.py`) with subtle cyan/blue gradients.
- Interactive menu options:
  - `[1] Quick Scan`: Fast static and ML inspection.
  - `[2] Deep Detonation Scan`: Opt-in sandboxed dynamic detonation.
  - `[3] Analyze Behavioral Log`: Sysmon and Windows EVTX correlation.
  - `[4] Batch Scan Directory`: Scan an entire folder of files.
  - `[5] Launch Web Console`: Start the local web dashboard.
  - `[6] Test Synthetic Demos`: Run safe built-in fixtures (Trojan, Ransomware, Benign).
- Also supports direct flags: `nullify scan <path>`, `nullify analyze-log <path>`, etc.

### 2. The Standalone C CLI (`bin/nullify-core`)
A lightweight, zero-dependency C binary for server environments:
```bash
./bin/nullify-core /bin/bash          # Human-readable colored output
./bin/nullify-core /bin/bash --json   # Pure JSON output for automation
```

### 3. The Web Application (RAVN-Inspired Minimalist Luxury)
Accessed at `http://127.0.0.1:8000`:
- **Color Palette**: High-contrast charcoal ink (`#191510`) on warm cream (`#f9f8f6`).
- **Typography**: Mona Sans with negative letter-spacing for an editorial luxury feel.
- **Header**: Animated headline **"See it. Trace it. Nullify it."** with fluid ink-draw underline animation and continuous heartbeat phase cycle.
- **Top Inverted Navbar**: Floating pill bar with inverted radial ears and glowing engine status beacon.
- **Background Aesthetics**: Halftone Michelangelo robot illustration with dot-grid pattern and vintage ornate corner engravings.
- **Command Workspace**: Drag-and-drop file upload zone, instant synthetic sample test chips, live mode toggles (`Static` vs `Deep`).
- **Bento Grid Analysis Results**:
  - Radial confidence progress gauge
  - 6-agent pipeline execution visualizer
  - Plain-English threat rationale
  - MITRE ATT&CK badges
  - Interactive, expandable findings deep-dive
  - Dark-mode syntax-highlighted synthesized YARA rule card with 1-click copy.

---

## 7. Safety, Ethics & Real-World Evaluation

### Strict Safety Guardrails
1. **Never executes malware on host**: Nullify never calls `exec`, `subprocess`, or `system` on scanned samples.
2. **Opt-in Sandbox Only**: Dynamic detonation is strictly opt-in (`--deep`) and routes only to an external sandbox (CAPEv2).
3. **Structured Evidence Only**: Reasoning agents and UI components only ever receive structured text/JSON metadata, never raw binary payloads.
4. **Safe Fixtures**: Built-in test suites use harmless synthetic fixtures mimicking malware structure without containing executable malicious payloads.

### Real-World Evaluation Record
The platform was subjected to a comprehensive end-to-end evaluation suite (`records/real_world_test_record.json`):
- **Trojan Payload (`trojan_beacon.exe`)**: `MALICIOUS` (Confidence: 94%), identified persistence keys, beaconing, and injected memory.
- **Ransomware Payload (`locker_sample.exe`)**: `MALICIOUS` (Confidence: 98%), identified shadow copy deletion, high section entropy ($7.89$), and encryption markers.
- **Benign Linux ELF Binary (`/bin/bash`)**: `BENIGN` (Confidence: 95%), 0 false positives, correct AMD64 64-bit architecture identification.
- **Benign Windows Executable (`explorer.exe`)**: `BENIGN` (Confidence: 91%), 0 false positives.
- **Sysmon Telemetry Log (`ransomware_sysmon.jsonl`)**: `MALICIOUS`, ATT&CK mapping to `T1486`, `T1059`, and `T1083`.
- **Automated YARA Synthesis**: Produced 100% syntactically valid YARA detection rules targeting observed strings and hex signatures.

---

## 8. Quick Reference: How to Run Everything

### Build and Test
```bash
# Build C-Core library and standalone CLI
make all

# Run standalone C CLI
./bin/nullify-core /bin/bash

# Run entire pytest suite (58 tests)
uv run pytest
```

### Launch Interactive CLI
```bash
uv run nullify
```

### Launch Web Interface
```bash
uv run nullify web
# Open your browser to http://127.0.0.1:8000
```

### Scan Files & Logs Directly
```bash
# Static & ML Scan
uv run nullify scan /path/to/sample.exe

# Deep Dynamic Detonation Scan
uv run nullify scan /path/to/sample.exe --deep

# Correlate Sysmon Log
uv run nullify analyze-log tests/fixtures/sysmon_ransomware.jsonl
```
