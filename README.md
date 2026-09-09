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

One engine, three interfaces — every interface calls the same orchestrator and
consumes the same streaming event bus; no analysis logic is duplicated.

```
Input (.exe / .dll / .evtx / .jsonl)
        │
   ┌────▼─────┐
   │  Triage   │  hashes, file type, entropy, reputation lookup
   └────┬─────┘
        ├──────────────────────┐
   ┌────▼─────┐         ┌──────▼──────┐
   │  Static   │         │  Dynamic     │  (opt-in sandbox, --deep)
   │  Analysis │         │  Analysis    │
   └────┬─────┘         └──────┬──────┘
        └────────────┬─────────┘
              ┌──────▼──────┐
              │ Classifier   │  v0: heuristic scorer · v1: XGBoost on EMBER
              └──────┬──────┘
              ┌──────▼──────┐
              │  Reasoning   │  evidence-cited plain-English verdict
              └──────┬──────┘
        CLI / TUI / Web UI  (shared event stream)
```

## Status (14-week milestone plan)

| Milestone | State |
|---|---|
| Phase 0 — scaffold, core engine, CLI, tests | ✅ done |
| Static agent: pefile + capa + YARA (weeks 3–4) | 🚧 heuristic imports/strings live, capa/YARA pending |
| Dynamic agent: CAPEv2 sandbox (weeks 5–6) | 🚧 interface ready, integration pending |
| Classifier: XGBoost on EMBER (weeks 7–8) | 🚧 heuristic scorer live, model pending |
| Log correlation: DARPA/Mordor + ATT&CK (weeks 9–10) | 🚧 JSON-lines/text live, EVTX pending |
| LangGraph orchestration + LLM reasoning (week 11) | 🚧 custom orchestrator live, optional LLM hook |
| TUI (week 12) · Web UI + scan-system (week 13) | 🔜 stubs in place |
| Evaluation & write-up (week 14) | 🔜 |

## Quickstart

```bash
make dev          # creates .venv via uv, installs runtime + dev/static extras
make test         # pytest

uv run nullify scan path/to/sample.exe            # static-only pipeline
uv run nullify scan path/to/sample.exe --json     # machine-readable report
uv run nullify scan path/to/sample.exe --deep     # opt-in sandbox detonation
uv run nullify analyze-log sysmon_export.jsonl    # behavioural log correlation
uv run nullify batch ./samples/ -o report.json    # directory batch scan
```

Optional extras: `pip install 'nullify[tui]'`, `nullify[web]`, `nullify[static]`,
`nullify[ml]`, `nullify[llm]` — see `pyproject.toml`.

## Repository layout

```
src/nullify/
├── core/
│   ├── agents/          # triage, static, dynamic, log_correlation, classifier, reasoning
│   ├── orchestrator.py  # pipeline + event streaming (the ONLY analysis entry point)
│   ├── models.py        # Finding / AgentResult / AnalysisResult dataclasses
│   └── events.py        # EventBus — one stream consumed by CLI, TUI, Web
├── interfaces/
│   ├── cli/             # typer app: scan, analyze-log, batch (+TUI stub)
│   └── web/             # FastAPI app (week 13)
docs/PLAN.md            # canonical capstone plan
datasets/ sandbox_configs/ tests/
```

## Development

```bash
make install   # runtime deps only
make dev       # + dev/static extras
make lint      # ruff check
make format    # ruff format
make test      # pytest
```

Conventions and hard rules for agents/contributors: see [AGENTS.md](AGENTS.md).

## License

MIT — see [LICENSE](LICENSE).
