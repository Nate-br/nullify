# NULLIFY
### Agentic AI-Powered Malware & Malware-Type Detection System
**Capstone Project Plan**

---

## 1. Executive Summary

**Nullify** is an agentic AI system that detects malware and classifies it by type (trojan, ransomware, spyware, worm, rootkit, etc.) by combining static analysis, sandboxed dynamic analysis, behavioral log correlation, and machine learning classification — synthesized by an LLM reasoning agent that explains *why* a verdict was reached, not just *what* it is.

Unlike traditional single-pass antivirus tools that rely primarily on hash/signature lookups, Nullify uses a pipeline of cooperating specialized agents that mimic how a human malware analyst investigates a sample: triage, static inspection, behavioral observation, classification, and reasoning — with the ability to escalate analysis when confidence is low.

Nullify ships with three interfaces built on one shared core engine:
- A **CLI** for analysts and scripting/batch workflows
- An interactive **TUI** (terminal UI) for live, visual single-scan analysis
- A **Web UI** for stakeholder-facing dashboards and reports

---

## 2. Problem Statement & Motivation

Most educational and open-source malware detection projects stop at hash matching against known-bad databases (e.g., VirusTotal lookups). This approach:
- Fails against any new, modified, or unseen (zero-day) sample
- Provides no insight into malware *behavior* or *family*
- Offers no explanation of *why* something was flagged

Real-world security operations require **behavior-based detection** with **explainability**, because analysts need to understand and trust a verdict before acting on it (e.g., isolating a host, triggering incident response).

Nullify's goal is to demonstrate that an agentic AI architecture — where multiple specialized agents each analyze different evidence and an LLM synthesizes their findings — produces more accurate, more explainable, and more realistic detection than a single black-box classifier or simple hash lookup.

---

## 3. Goals & Non-Goals

### Goals
- Detect malware in submitted files (primarily Windows PE executables)
- Classify detected malware into behavioral types: trojan, ransomware, spyware, worm, rootkit, and others as scoped
- Correlate file-based findings with endpoint behavioral logs (Sysmon/EVTX)
- Provide human-readable, evidence-based explanations for every verdict
- Map findings to MITRE ATT&CK techniques for industry-standard framing
- Support CLI, TUI, and Web UI on a single shared core engine
- Support both single-file scans and full-system/directory scans

### Non-Goals (explicitly out of scope for v1)
- Building live endpoint sensor agents deployed across a fleet of machines
- Real-time network traffic capture/analysis (deferred to future work)
- Automated remediation/quarantine actions
- Cross-platform malware (macOS/Linux) beyond basic ELF static support — PE/Windows is the primary target
- Auto-executing arbitrary files found during a live system scan in a sandbox (high risk; deep/dynamic analysis is only triggered on explicitly submitted samples)

---

## 4. System Architecture

### 4.1 High-Level Pipeline

```
                         ┌─────────────────────┐
                         │   Input: File / Log   │
                         │  (.exe, .dll, .evtx)  │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │    Triage Agent      │
                         │  hash lookup, file    │
                         │  type ID, entropy,    │
                         │  quick filter         │
                         └──────────┬───────────┘
                                    │
                 ┌──────────────────┼──────────────────┐
                 ▼                  ▼                  ▼
      ┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
      │  Static Analysis    │ │ Dynamic Analysis    │ │ Log Correlation     │
      │  Agent               │ │ Agent (sandbox)      │ │ Agent                │
      │  pefile, capa,       │ │ CAPEv2, behavior      │ │ Sysmon/EVTX parsing, │
      │  YARA, strings        │ │ capture               │ │ ATT&CK technique     │
      │                      │ │                       │ │ matching             │
      └──────────┬───────────┘ └──────────┬───────────┘ └──────────┬───────────┘
                 └──────────────────┬──────────────────┘
                                    ▼
                         ┌─────────────────────┐
                         │ Classification Agent │
                         │  ML model: benign/    │
                         │  malware + family     │
                         └──────────┬───────────┘
                                    ▼
                         ┌─────────────────────┐
                         │  Reasoning Agent (LLM) │
                         │  synthesizes evidence, │
                         │  writes explanation,   │
                         │  may request re-scan   │
                         └──────────┬───────────┘
                                    ▼
                         ┌─────────────────────┐
                         │   Verdict + Report    │
                         │  CLI / TUI / Web UI    │
                         └─────────────────────┘
```

### 4.2 Agent Responsibilities

| Agent | Responsibility | Key Tools |
|---|---|---|
| **Triage** | Cheap first-pass filtering: hash lookup, file type detection, entropy check, decide whether to escalate | VirusTotal API, MalwareBazaar API, `python-magic` |
| **Static Analysis** | Inspect file without execution: imports, strings, embedded IOCs, capability matching | `pefile`, `capa`, `yara-python` |
| **Dynamic Analysis** | Execute sample in isolated sandbox, capture behavior | CAPEv2 / Cuckoo Sandbox |
| **Log Correlation** | Ingest Sysmon/EVTX logs (from sandbox runs or provided datasets), detect suspicious process trees, persistence, lateral movement | Custom parser, MITRE ATT&CK mapping |
| **Classification** | Predict benign/malicious + malware family from combined feature vector | XGBoost / scikit-learn, trained on EMBER/SOREL-20M |
| **Reasoning** | Synthesize all agent outputs into a plain-English, evidence-cited verdict; request additional analysis if confidence is low | Claude API (structured input, not raw binaries) |
| **Orchestrator** | Coordinates agent execution order, manages state, streams progress to interfaces | LangGraph or custom state machine |

### 4.3 Core Design Principle: One Engine, Three Interfaces

All three interfaces call the same orchestrator function and never re-implement analysis logic:

```
orchestrator.run(input, mode) -> AnalysisResult
```

The orchestrator exposes streaming callbacks (`on_agent_start`, `on_agent_complete`, `on_finding`) so the CLI's verbose mode, the TUI's live panels, and the web UI's progress timeline all consume the identical event stream.

---

## 5. Interfaces & User Workflows

### 5.1 CLI

For analysts, scripting, and batch/automation workflows.

```bash
# Quick static-only scan
nullify scan suspicious.exe

# Full scan including sandbox detonation
nullify scan suspicious.exe --deep

# Analyze existing behavioral logs, no file needed
nullify analyze-log sysmon_export.evtx

# Batch scan a directory, machine-readable output
nullify batch ./samples/ --output report.json --format json

# Verbose narrated output (agent-by-agent, good for demos)
nullify scan suspicious.exe --deep --verbose

# Full or targeted system scan
nullify scan-system                 # quick scan: common malware hiding spots
nullify scan-system --full          # walk entire filesystem
nullify scan-system --path C:\Users\ --exclude node_modules,WinSxS
```

Example `--verbose` narration:
```
[Triage]     No hash match found — proceeding to full analysis
[Static]     Extracted 47 imports, entropy 7.8 (likely packed)
[Static]     capa: matches "inject into remote process", "persist via registry run key"
[Dynamic]    Sandbox: spawned svchost.exe, created scheduled task, beaconed to 185.x.x.x
[Classifier] 94% confidence — Trojan (Remote Access family)
[Reasoning]  This sample injects code into a legitimate process, establishes
             persistence via a registry run key, and beacons outbound —
             behavior consistent with a Remote Access Trojan, not
             ransomware or spyware.
```

### 5.2 TUI (Terminal UI) — REMOVED per user direction (superseded by the professional web UI)

Built with **Textual** (Python), for interactive live-scan demos.

```
┌─ Nullify ─────────────────────────────────────────────────────┐
│ Target: suspicious.exe                    Mode: Deep Scan     │
├─────────────────────────────────────────────────────────────────┤
│ Pipeline Progress                                               │
│  ✓ Triage           No hash match, escalating                  │
│  ✓ Static Analysis  47 imports, entropy 7.8 (packed)            │
│  ⟳ Dynamic Analysis Running in sandbox... [██████░░░░] 60%     │
│  ○ Classification   pending                                      │
│  ○ Reasoning        pending                                      │
├─────────────────────────────────────────────────────────────────┤
│ Live Findings                          │ Details Pane            │
│ • capa: process injection      [HIGH]  │ Import: CreateRemote    │
│ • capa: registry persistence   [MED]   │ Thread                  │
│ • Sandbox: outbound beacon     [HIGH]  │ Used by 87% of RAT      │
│                                          │ samples in training     │
├─────────────────────────────────────────────────────────────────┤
│ [q] quit  [d] deep details  [r] rerun  [e] export report        │
└─────────────────────────────────────────────────────────────────┘
```

```bash
nullify scan suspicious.exe --tui
```

### 5.3 Web UI

For stakeholder-facing demos and shareable reports.

- **Backend**: FastAPI wrapping the same orchestrator; `/scan` endpoint for file upload; WebSocket endpoint for live agent-progress streaming
- **Frontend**: file upload/drag-and-drop, live agent-progress timeline, results view with verdict, confidence score, matched ATT&CK techniques, and the LLM's plain-English explanation

### 5.4 Who Uses What

| Interface | User | Use Case |
|---|---|---|
| CLI | Analyst / you (dev) | Fast iteration, scripting, batch analysis, CI-style automation |
| TUI | Live demo audience | Visual, real-time single-scan walkthrough |
| Web UI | Non-technical stakeholder / committee | Upload-and-view experience, shareable reports |

---

## 6. Malware Behavior Recognition (Beyond Hash Lookup)

Detection signal is drawn from both static and dynamic evidence, then vectorized for classification.

### 6.1 Static Indicators by Malware Type

| Type | Static Signals |
|---|---|
| **Trojan** | Imports: `URLDownloadToFile`, `WinExec`, `CreateRemoteThread`; hardcoded IPs/URLs in strings |
| **Spyware** | Imports: `SetWindowsHookEx`, `GetAsyncKeyState` (keylogging), `BitBlt` (screen capture), `GetClipboardData` |
| **Ransomware** | Imports: `CryptEncrypt`, `CryptGenKey`; `FindFirstFile` loops (mass file enumeration); ransom-note strings |
| **Worm** | Self-replication write patterns; network share enumeration APIs |
| **Rootkit** | Driver-loading APIs; SSDT/hook-related imports; kernel object manipulation |

`capa` (FLARE's capability-detection tool) encodes hundreds of these behavior-to-capability rules and is the fastest path to reliable static signal without hand-writing every rule.

### 6.2 Dynamic (Sandbox) Indicators

- Process tree shape (e.g., `cmd.exe → powershell.exe` spawn chains: classic dropper pattern)
- Registry writes to `Run` keys (persistence)
- Mass file rename/encryption in a short time window (ransomware signature)
- Network beaconing intervals, DNS tunneling patterns (C2 activity)

### 6.3 From Rules to a Classifier

1. Vectorize `capa` matches, import lists, and dynamic behavior events into a per-sample feature vector
2. Train a multi-class model (XGBoost recommended) on **EMBER** and/or **SOREL-20M** to predict: benign / trojan / ransomware / spyware / worm / rootkit
3. Map static and dynamic evidence to **MITRE ATT&CK** techniques as an interpretability layer
4. Feed capa matches + ATT&CK mapping + classifier confidence into the Reasoning Agent for the final natural-language explanation

---

## 7. Full-System Scanning Strategy

Real AV tools scan in layers rather than brute-force, for both speed and coverage. Nullify follows the same model:

1. **File enumeration** — walk the filesystem with sane exclusions (`WinSxS`, `node_modules`, VM disk images, etc.)
2. **Cheap filtering** — skip unchanged files via hash cache, skip files below a size threshold, skip signed binaries from trusted publishers
3. **Static analysis** — run only on executable/script file types (`.exe`, `.dll`, `.scr`, `.ps1`, `.vbs`, `.bat`, `.js`, macro-enabled Office docs)
4. **Dynamic/sandbox analysis** — reserved for explicitly submitted samples only; never auto-triggered on files found during a live system scan (safety boundary)

Scan modes:
```bash
nullify scan-system --quick   # startup folders, temp, downloads, Run keys, scheduled tasks
nullify scan-system --full    # full filesystem walk, filtered to executable types
```

Performance considerations: hash caching to skip unchanged files, multi-threaded file walking.

---

## 8. Datasets

| Dataset | Purpose |
|---|---|
| **EMBER** | 1.1M labeled PE feature vectors (benign/malicious); primary classifier training data |
| **SOREL-20M** | Larger labeled corpus with richer family/type metadata |
| **MalwareBazaar** | Labeled malware samples for static/dynamic pipeline testing |
| **VirusShare** | Additional labeled sample corpus |
| **DARPA Transparent Computing** | Pre-recorded realistic endpoint/behavioral logs with known attack scenarios |
| **OTRF Mordor Project** | Sysmon/process-tree datasets mapped to ATT&CK techniques |
| **MITRE ATT&CK** | Technique taxonomy for detection mapping and reporting |

All malware sample handling occurs in isolated, network-restricted sandbox environments only.

---

## 9. Technology Stack

| Layer | Technology |
|---|---|
| Static analysis | `pefile`, `capa`, `yara-python` |
| Sandbox | CAPEv2 (or Cuckoo Sandbox), isolated VM, no network egress by default |
| Classification | XGBoost / scikit-learn |
| Agent orchestration | LangGraph (or custom state machine) |
| LLM reasoning | Claude API, given structured JSON evidence — never raw binaries |
| CLI | Python, `click` or `typer` |
| TUI | Textual |
| Web backend | FastAPI |
| Web frontend | React (or minimal HTML/JS) |
| Log parsing | Custom Sysmon/EVTX parser |

---

## 10. Repository Structure

```
nullify/
├── core/
│   ├── agents/
│   │   ├── triage.py
│   │   ├── static_analysis.py
│   │   ├── dynamic_analysis.py
│   │   ├── log_correlation.py
│   │   ├── classifier.py
│   │   └── reasoning.py
│   ├── orchestrator.py         # runs pipeline, streams events, returns AnalysisResult
│   └── models/                 # trained classifier artifacts, feature extractors
├── cli/
│   ├── main.py                 # entrypoint, plain vs TUI mode
│   ├── plain_output.py         # verbose/JSON output, scriptable
│   └── tui/
│       ├── app.py              # Textual App
│       └── widgets/
│           ├── pipeline_progress.py
│           ├── findings_table.py
│           └── verdict_screen.py
├── web/
│   ├── backend/                # FastAPI app
│   └── frontend/               # dashboard UI
├── datasets/
├── sandbox_configs/
└── tests/
```

---

## 11. Evaluation Plan

A capstone must demonstrate rigor, not just a working demo. Evaluation includes:

- **Precision/recall per malware family** (not just overall accuracy) — multi-class confusion matrix across benign/trojan/ransomware/spyware/worm/rootkit
- **False positive rate** on a held-out benign sample set (critical — high false positives make a detector unusable in practice)
- **Baseline comparison** — the full agentic pipeline (static + dynamic + log correlation + classifier + reasoning) vs. a single-model baseline (classifier on static features alone), to demonstrate the agentic approach's added value
- **Explainability assessment** — qualitative review of whether Reasoning Agent explanations correctly cite the evidence that drove the verdict
- **ATT&CK coverage** — which techniques the system successfully detects and maps
- **Performance** — scan time for quick vs. deep vs. full-system modes

---

## 12. Safety, Legal & Ethical Considerations

- All malware execution occurs exclusively inside isolated, network-restricted sandbox VMs — never on host systems
- Sample storage is encrypted and access-controlled
- Institutional/coursework policy on possessing malware samples for research must be confirmed before acquiring samples from MalwareBazaar/VirusShare
- Full-system scans never auto-execute discovered files in a sandbox; dynamic analysis is only triggered on explicitly submitted samples
- The Reasoning Agent (LLM) receives only structured, pre-processed evidence (feature vectors, capa matches, log summaries) — never raw binary content — both for safety and because LLMs are not reliable binary analyzers
- Demo environments use a curated mix of known-benign files and vetted test samples from MalwareBazaar/EMBER test splits rather than live-scanning production or personal machines

---

## 13. Timeline (14 Weeks)

| Weeks | Milestone |
|---|---|
| 1–2 | Literature review, finalize scope, set up sandbox (CAPEv2 VM), acquire datasets |
| 3–4 | Static Analysis Agent: `pefile` + `capa` + YARA integration |
| 5–6 | Dynamic Analysis Agent: sandbox execution, Sysmon log capture, behavioral feature extraction |
| 7–8 | Classification model: train on EMBER, evaluate confusion matrix across families |
| 9–10 | Log Correlation Agent: ingest DARPA/Mordor datasets, ATT&CK technique detection |
| 11 | Orchestrator + Reasoning Agent: LangGraph pipeline, Claude-based explanation synthesis |
| 12 | CLI (plain + TUI) built on orchestrator streaming interface |
| 13 | Web UI (FastAPI backend + dashboard frontend), full-system scan mode |
| 14 | End-to-end testing, evaluation write-up, demo preparation |

---

## 14. Future Work

- Cross-platform support (ELF/Mach-O, script-based malware: PowerShell, macros)
- Live endpoint sensor deployment for real-time behavioral monitoring at scale
- Network traffic analysis integration (PCAP/NetFlow)
- Automated response actions (quarantine, host isolation) with human-in-the-loop approval
- Continuous learning pipeline to retrain the classifier on newly triaged samples
- Multi-agent adversarial testing (red-team the detector against evasion techniques)

---

## 15. Success Criteria

Nullify will be considered successful if it can:
1. Correctly classify malware type with meaningfully higher per-family precision/recall than a static-features-only baseline
2. Produce human-readable, evidence-cited explanations for at least 90% of flagged samples in manual review
3. Complete a quick system scan in under a target time budget (to be set after performance testing) on a representative demo environment
4. Demonstrate the full pipeline live via CLI/TUI and Web UI without manual intervention
