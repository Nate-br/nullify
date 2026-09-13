---
tags:
  - agent
  - classifier
  - machine-learning
  - xgboost
title: "Agent 5: Classifier Agent"
date: 2026-09-13
---

# 🧠 Agent 5: Classifier Agent

The **Classifier Agent** computes a machine learning inference score for Windows PE binaries based on the [[03 - Data & Intelligence/EMBER 2017 Dataset|EMBER 2017 v2]] feature specification.

---

## Machine Learning Stack
- **Model**: [[05 - Machine Learning/XGBoost Architecture & Training|XGBoost (XGBClassifier)]]
- **Feature Vector**: 2,381 dimensions
- **Accuracy**: **99.46%**
- **Precision**: **99.60%**
- **False Positive Rate (FPR)**: **0.39%**

---

## Decision Thresholds

The Classifier outputs a probability $P(\text{malicious}) \in [0.0, 1.0]$:
- **$P \ge 0.85$**: `MALICIOUS` (High-confidence malware)
- **$0.40 \le P < 0.85$**: `SUSPICIOUS` (Anomalous structure, requires analyst review)
- **$P < 0.40$**: `BENIGN` (Normal software characteristics)

---

## The Linux ELF / Non-PE Gating Mechanism

> [!important] Cross-Platform False Positive Elimination
> The EMBER model was trained strictly on Windows PE headers. When analyzing Linux ELF binaries (`/bin/bash`) or scripts, the binary lacks PE sections and import tables.
> 
> If fed to EMBER blindly, the missing Windows structures cause the model to flag the file as "heavily obfuscated Windows malware."
> 
> Nullify includes an **intelligent gating check**:
> ```python
> if not self._is_pe(target):
>     # Bypass Windows PE model on Linux ELF / scripts
>     return AgentResult(agent=self.name, status=AgentStatus.SKIPPED, ...)
> ```
> This guarantees **0% false alarms** on Linux executables.

---

## Related Notes
- [[Multi-Agent Pipeline|Multi-Agent Pipeline]]
- [[03 - Data & Intelligence/EMBER 2017 Dataset|EMBER 2017 Dataset]]
- [[05 - Machine Learning/XGBoost Architecture & Training|XGBoost Architecture & Training]]
- [[05 - Machine Learning/Verdict Fusion Logic|Verdict Fusion Logic]]
