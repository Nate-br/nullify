---
tags:
  - runbook
  - operations
  - commands
  - cheatsheet
title: "Runbook & Operational Commands"
date: 2026-09-13
---

# 🛠️ Runbook & Operational Commands

A quick reference cheatsheet for building, running, scanning, testing, and training with Nullify.

---

## 1. Building the Native C-Core

```bash
# Compile lib/libnullify.so and bin/nullify-core
make all

# Clean build artifacts
make clean
```

---

## 2. Running Standalone C Triage

```bash
# Human-readable colored output with execution latency
./bin/nullify-core /path/to/binary

# Pure JSON output for automation
./bin/nullify-core /path/to/binary --json
```

---

## 3. Running the Python Pipeline

```bash
# Launch interactive terminal console
uv run nullify

# Direct static and ML scan
uv run nullify scan /path/to/sample.exe

# Opt-in deep dynamic detonation scan
uv run nullify scan /path/to/sample.exe --deep

# Correlate endpoint telemetry log
uv run nullify analyze-log /path/to/sysmon_log.jsonl

# Batch scan an entire folder of files
uv run nullify batch ./samples/ -o scan_report.json

# Launch the Web UI dashboard
uv run nullify web
# Access at http://127.0.0.1:8000
```

---

## 4. Running the Test Suite

```bash
# Run all 58 automated tests
uv run pytest

# Run C-engine acceleration tests only
uv run pytest tests/test_c_engine.py -v
```

---

## 5. Retraining the ML Model

```bash
# 1. Cloud GPU Retraining (Recommended):
# Open notebooks/train_nullify_colab.ipynb in Google Colab

# 2. Local Training Pipeline:
uv run python scripts/vectorize_ember.py --input datasets/ember/ --output datasets/ember/ember_vectors.npz
uv run python scripts/train_ember_xgb.py --vectors datasets/ember/ember_vectors.npz --out models/malware_xgb.json
```

---

## Related Notes
- [[00 - Master Index/Dashboard|Dashboard]]
- [[Real-World Evaluation Record|Real-World Evaluation Record]]
- [[04 - Native C Engine/Native C-Core Accelerator|Native C-Core Accelerator]]
