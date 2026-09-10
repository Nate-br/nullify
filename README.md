# Nullify

**Agentic AI-powered malware & malware-type detection system** — capstone project.
Canonical plan: [docs/PLAN.md](docs/PLAN.md).

Nullify detects malware and classifies it by behavioural type (trojan, ransomware,
spyware, worm, rootkit) using a pipeline of cooperating analysis agents — triage,
static inspection, sandboxed detonation, log correlation and ML classification —
synthesised by a reasoning layer that explains *why* a verdict was reached, mapped
to MITRE ATT&CK.

Unlike single-pass AV tools that stop at hash lookups, Nullify mimics how a human
analyst investigates a sample: cheap filtering first, escalating to deeper analysis
when evidence warrants it.

> ⚠️ **Safety boundary**: Nullify never executes analysed samples on the host.
> Dynamic analysis is strictly opt-in (`--deep`) and only targets an externally
> configured sandbox (CAPEv2). The reasoning layer receives structured evidence
> only — never raw binaries.

## Architecture

One engine, two interfaces — every interface calls the same orchestrator and
consumes the same streaming event bus; no analysis logic is duplicated.

```
Input (.exe / .dll / .evtx / .jsonl)
        │
   ┌────▼─────┐
   │  Triage  │  hashes, file type, entropy, reputation lookup
   └────┬─────┘
        ├──────────────────────┐
   ┌────▼─────┐         ┌──────▼──────┐
   │  Static  │         │  Dynamic    │  (opt-in sandbox, --deep)
   │ Analysis │         │ Analysis    │
   └────┬─────┘         └──────┬──────┘
        └────────────┬─────────┘
              ┌──────▼──────┐
              │ Log Correl. │  Sysmon logs to ATT&CK mapping
              └──────┬──────┘
              ┌──────▼──────┐
              │ Classifier  │  XGBoost on EMBER
              └──────┬──────┘
              ┌──────▼──────┐
              │ Reasoning   │  evidence-cited plain-English verdict
              └──────┬──────┘
        CLI / Web UI  (shared event stream)
```

## Locally-trained XGBoost EMBER Classifier

The system features a custom classification agent using an XGBoost model trained on the EMBER dataset. Evaluated on a 500K-row balanced sample, the classifier achieved **99.46% accuracy** and a **0.39% False Positive Rate (FPR)**. This provides robust file-based confidence scores alongside static evidence and MITRE ATT&CK mapping.

## YARA Rules Summary

The static agent evaluates files against a suite of behavioral and structural YARA rules. Instead of hardcoded hash signatures, these rules match common malware capabilities, packed indicators, and suspicious string structures, helping to drive the Reasoning Agent's explanations.

## Interfaces and Usage

Nullify exposes two interfaces for interacting with the single core engine:

### 1. CLI (Command-Line Interface)
Perfect for terminal users, scripting, and batch analysis.
```bash
uv run nullify scan path/to/sample.exe            # static-only pipeline
uv run nullify scan path/to/sample.exe --deep     # opt-in sandbox detonation
uv run nullify analyze-log sysmon_export.jsonl    # behavioural log correlation
uv run nullify batch ./samples/ -o report.json    # directory batch scan
```

### 2. Web UI
A terminal-core styled analysis console (pure black, monospace, single green
accent): ascii confidence bar, color-coded verdict, list-style agent pipeline,
severity-badged findings, and a plain-english rationale — all served locally,
no build step.

Includes an offline AI chat assistant to explain verdicts and findings. To use the chat feature, install all extras (`uv sync --all-extras` — a plain `uv sync --extra llm` would *remove* your other dependency groups) and place the `qwen2.5-3b-instruct-q4_k_m.gguf` model in `models/llm/`.
```bash
uv run nullify web                                # Starts the FastAPI backend
# Navigate to http://127.0.0.1:8000
```

## Safety and Ethics

- **Synthetic Targets Only**: No real, un-isolated malware is packaged or executed on the host system during tests.
- **Local Analysis**: The core architecture supports entirely local analysis utilizing the local XGBoost model, with no raw binary data ever sent to external APIs without explicit user configuration.
- **Opt-in Detonation**: Dynamic sandbox environments are strictly opt-in using the `--deep` flag to prevent accidental execution.

## Development Setup

```bash
make install   # runtime deps only
make dev       # installs runtime + every extra (uv sync --all-extras)
make lint      # ruff check src tests scripts
make format    # ruff format src tests scripts
make test      # pytest
```

## Repository layout

```
src/nullify/
├── core/
│   ├── agents/          # triage, static, dynamic, log_correlation, classifier, reasoning
│   ├── orchestrator.py  # pipeline + event streaming (the ONLY analysis entry point)
│   ├── models.py        # Finding / AgentResult / AnalysisResult dataclasses
│   └── events.py        # EventBus — one stream consumed by CLI, Web
├── interfaces/
│   ├── cli/             # typer app: scan, analyze-log, batch
│   └── web/             # FastAPI app + static frontend (index.html, style.css, app.js)
docs/PLAN.md            # canonical capstone plan
datasets/ sandbox_configs/ tests/
```

## License

MIT — see [LICENSE](LICENSE).
