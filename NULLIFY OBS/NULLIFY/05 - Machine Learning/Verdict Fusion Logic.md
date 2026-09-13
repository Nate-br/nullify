---
tags:
  - machine-learning
  - fusion
  - safety
  - verdicts
title: "Verdict Fusion Logic & Decision Rules"
date: 2026-09-13
---

# 🛡️ Verdict Fusion Logic & Decision Rules

Machine learning models produce statistical probabilities, not absolute facts. In a security operations center, blind reliance on ML output leads to false alarms on critical enterprise software.

Nullify implements **Verdict Fusion**: a strict hierarchical logic connecting deterministic evidence with probabilistic ML predictions.

---

## The Fusion Hierarchy

```
┌────────────────────────────────────────────────────────┐
│             LEVEL 1: GROUND TRUTH EVIDENCE             │
│   YARA rule matches, verified ransomware commands,     │
│       malicious persistence keys, Trojan drops.        │
└───────────────────────────┬────────────────────────────┘
                            │ (Overrides everything)
                            ▼
┌────────────────────────────────────────────────────────┐
│          LEVEL 2: MACHINE LEARNING ESCALATION          │
│   If static evidence is inconclusive, ML probability   │
│          P >= 0.85 escalates verdict to MALICIOUS.     │
└───────────────────────────┬────────────────────────────┘
                            │ (Can escalate, NEVER downgrade)
                            ▼
┌────────────────────────────────────────────────────────┐
│             LEVEL 3: PLATFORM ARCHITECTURE             │
│   Non-PE binaries (Linux ELF / scripts) bypass the     │
│   Windows PE ML model to guarantee zero false alarms.  │
└────────────────────────────────────────────────────────┘
```

---

## Core Operational Rules

1. **Evidence is King**: If [[02 - Architecture & Agents/Agent - Static Analysis|Static Analysis]] or [[02 - Architecture & Agents/Agent - Log Correlation|Log Correlation]] detects malicious commands, the verdict is `MALICIOUS` even if the ML probability is low.
2. **Escalation Only**: An ML probability of $P \ge 0.85$ can escalate a borderline file to `MALICIOUS`, but a low ML probability can **never downgrade** confirmed malicious evidence.
3. **Format Gating**: The Windows PE EMBER model is gated to Windows executables only. Linux ELF files rely on ELF static triage, eliminating cross-platform false alarms.

---

## Related Notes
- [[XGBoost Architecture & Training|XGBoost Architecture & Training]]
- [[02 - Architecture & Agents/Agent - Classifier|Agent 5: Classifier]]
- [[02 - Architecture & Agents/Agent - Reasoning|Agent 6: Reasoning]]
