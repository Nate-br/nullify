---
tags:
  - agent
  - reasoning
  - synthesis
  - mitre
  - yara
title: "Agent 6: Reasoning Agent"
date: 2026-09-13
---

# ⚖️ Agent 6: Reasoning Agent

The **Reasoning Agent** serves as the executive intelligence of the Nullify platform. It synthesizes findings across all previous agents, attributes the specific malware family, writes plain-English explanations, and generates actionable countermeasures.

---

## 1. Evidence Aggregation & Verdict Determination

Rather than trusting any single tool, the Reasoning Agent weighs all evidence:
- If [[Agent - Static Analysis|Static Analysis]] finds confirmed ransomware signatures (e.g. shadow copy deletion commands, known ransom note extensions), the verdict is `MALICIOUS`.
- If [[Agent - Classifier|Classifier]] predicts $P \ge 0.85$, it escalates a borderline sample to `MALICIOUS`.
- If a sample is a benign Linux ELF binary with 0 findings, it issues a clean `BENIGN` verdict with high confidence.

---

## 2. Threat Family Attribution

The agent categorizes malicious samples into specific threat families:
- **Trojan**: Backdoor persistence, remote injection, C2 beacons.
- **Ransomware**: Mass encryption, shadow copy destruction, high entropy.
- **Spyware / InfoStealer**: Browser credential access, keystroke hooks.
- **Worm**: Autonomous network spreading, SMB exploitation.
- **Rootkit**: Kernel driver loading, process hiding.

---

## 3. Automated YARA Rule Synthesis

When a threat is confirmed, the Reasoning Agent automatically synthesizes a custom, syntactically valid **YARA detection rule**:
- Targets the specific strings, section names, and hex byte patterns observed during triage.
- Ready to be deployed into corporate EDR / SIEM solutions with 1 click.

---

## Related Notes
- [[Multi-Agent Pipeline|Multi-Agent Pipeline]]
- [[03 - Data & Intelligence/MITRE ATT&CK Mapping|MITRE ATT&CK Mapping]]
- [[03 - Data & Intelligence/YARA Synthesis|YARA Synthesis]]
- [[05 - Machine Learning/Verdict Fusion Logic|Verdict Fusion Logic]]
