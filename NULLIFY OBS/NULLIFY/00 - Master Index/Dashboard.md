---
tags:
  - moc
  - nullify
  - dashboard
  - cybersecurity
title: "🛡️ Nullify Knowledge Base & Master MOC"
date: 2026-09-13
---

# 🛡️ Nullify Threat Intelligence Platform
> *"See it. Trace it. Nullify it."*  
> An Agentic AI-Powered Malware Detection & Threat Intelligence System

```
       ┌────────────────────────────────────────────────────────┐
       │                 NULLIFY VAULT MAP                      │
       ├────────────────────────────────────────────────────────┤
       │  [[01 - Overview/Concept & Philosophy|01 - Overview]]                  │
       │  [[02 - Architecture & Agents/Multi-Agent Pipeline|02 - Architecture & Agents]]    │
       │  [[03 - Data & Intelligence/EMBER 2017 Dataset|03 - Data & Intelligence]]        │
       │  [[04 - Native C Engine/Native C-Core Accelerator|04 - Native C Acceleration]]     │
       │  [[05 - Machine Learning/XGBoost Architecture & Training|05 - Machine Learning]]           │
       │  [[06 - Interfaces & Design/Luxury Editorial Web UI|06 - UI & Terminal Experience]]   │
       │  [[07 - Verification & Runbook/Real-World Evaluation Record|07 - Testing & Operations]]        │
       └────────────────────────────────────────────────────────┘
```

---

## ⚡ System Vital Stats

> [!summary] Key Project Metrics
> - **Architecture**: 6 Cooperating AI Agents with Shared Event Bus
> - **Inference Acceleration**: Native C (`-O3 -std=c11`) with `ctypes` bridge
> - **ML Model**: XGBoost Classifier on EMBER 2017 v2 (2,381 feature dimensions)
> - **Accuracy**: **99.46%** | **Precision**: **99.60%** | **FPR**: **0.39%**
> - **Triage Latency**: $< 15\text{ ms}$ on multi-megabyte binaries
> - **Test Suite**: **58/58 unit & integration tests passing**
> - **Cloud GPU Training**: 1-Click Google Colab Notebook with CUDA acceleration

---

## 🧭 Vault Navigation (Map of Content)

### 1. [[01 - Overview/Concept & Philosophy|01 - Concept & Philosophy]]
- The Problem: Why traditional antivirus & single-pass sandboxes fail
- The Solution: Mimicking human malware analyst workflows
- Safety & Ethics: Air-gapped host, strictly opt-in detonation

### 2. [[02 - Architecture & Agents/Multi-Agent Pipeline|02 - Architecture & The 6 Agents]]
- [[02 - Architecture & Agents/Agent - Triage|Agent 1: Triage Agent]] (Fast C filtering, magic bytes, entropy, hashes)
- [[02 - Architecture & Agents/Agent - Static Analysis|Agent 2: Static Analysis Agent]] (PE/ELF dissection, sections, YARA)
- [[02 - Architecture & Agents/Agent - Dynamic Detonation|Agent 3: Dynamic Detonation Agent]] (CAPEv2 sandbox connector)
- [[02 - Architecture & Agents/Agent - Log Correlation|Agent 4: Log Correlation Agent]] (Sysmon & Windows EVTX logs)
- [[02 - Architecture & Agents/Agent - Classifier|Agent 5: Classifier Agent]] (2,381-dim XGBoost & non-PE gating)
- [[02 - Architecture & Agents/Agent - Reasoning|Agent 6: Reasoning Agent]] (Evidence synthesis, MITRE ATT&CK, YARA generator)

### 3. [[03 - Data & Intelligence/EMBER 2017 Dataset|03 - Data & Intelligence]]
- [[03 - Data & Intelligence/EMBER 2017 Dataset|The EMBER 2017 v2 Dataset]] (1.1M binaries, breakdown of all 2,381 dims)
- [[03 - Data & Intelligence/Sysmon & Event Telemetry|Sysmon Telemetry & Event IDs]] (Process creation, network C2, injection)
- [[03 - Data & Intelligence/MITRE ATT&CK Mapping|MITRE ATT&CK Framework]] (Tactics & Techniques taxonomy)

### 4. [[04 - Native C Engine/Native C-Core Accelerator|04 - Performance & Native C Accelerator]]
- [[04 - Native C Engine/Native C-Core Accelerator|Native C Engine Architecture]] (`libnullify.so` & `bin/nullify-core`)
- [[04 - Native C Engine/Python ctypes Bridge|Python ctypes Bridge]] (`c_engine.py` with seamless pure-Python fallback)
- Benchmarks: 7.1x speedup on byte entropy, 5.2x on string scanning

### 5. [[05 - Machine Learning/XGBoost Architecture & Training|05 - Machine Learning]]
- [[05 - Machine Learning/XGBoost Architecture & Training|XGBoost Architecture]] (Hyperparameters, hist tree method)
- [[05 - Machine Learning/Verdict Fusion Logic|Verdict Fusion Logic]] (Evidence ground-truth vs probabilistic escalation)
- [[05 - Machine Learning/Google Colab GPU Training|Google Colab Cloud GPU Training]] (`notebooks/train_nullify_colab.ipynb`)

### 6. [[06 - Interfaces & Design/Luxury Editorial Web UI|06 - Interfaces & User Experience]]
- [[06 - Interfaces & Design/Luxury Editorial Web UI|Luxury Editorial Web UI]] (useravn.com aesthetic, charcoal on cream, Mona Sans)
- [[06 - Interfaces & Design/Interactive CLI & ASCII Art|Interactive CLI & ASCII Art]] (Truecolor banner, interactive menu)

### 7. [[07 - Verification & Runbook/Real-World Evaluation Record|07 - Verification & Operations]]
- [[07 - Verification & Runbook/Real-World Evaluation Record|Real-World Test Suite Record]] (Trojan, Ransomware, Benign ELF/PE, Sysmon)
- [[07 - Verification & Runbook/Runbook & Commands|Runbook & Quick Commands]] (How to build, scan, train, and test)

---

> [!tip] Continuous Reading
> If you prefer a single master document from start to finish, see [[00 - Master Index/Nullify Master Guide|Nullify Master Guide]].
