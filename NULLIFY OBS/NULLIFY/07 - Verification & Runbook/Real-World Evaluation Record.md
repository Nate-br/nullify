---
tags:
  - testing
  - records
  - verification
  - ground-truth
title: "Real-World Evaluation Record"
date: 2026-09-13
---

# 📋 Real-World Evaluation Record

Nullify was rigorously tested against real-world sample formats, benign operating system files, enterprise telemetry logs, and synthetic fixtures to verify accuracy, confidence calculations, and false positive prevention.

Full audit records are stored in `records/real_world_test_record.json`.

---

## Evaluation Results Matrix

| Target Sample | Target Type | Verdict | Confidence | Key Evidence Observed |
| :--- | :--- | :---: | :---: | :--- |
| **`trojan_beacon.exe`** | Windows PE | `MALICIOUS` | **94%** | C2 beaconing pattern, persistence run key, remote injection. |
| **`locker_sample.exe`** | Windows PE | `MALICIOUS` | **98%** | Shannon entropy **7.89** (encrypted), shadow copy deletion. |
| **`/bin/bash`** | Linux ELF | `BENIGN` | **95%** | Correct AMD64 64-bit triage, zero false positives. |
| **`explorer.exe`** | Windows PE | `BENIGN` | **91%** | Standard Microsoft digital signature, benign import table. |
| **`sysmon_ransomware.jsonl`**| Telemetry | `MALICIOUS` | **96%** | `vssadmin` execution, Event IDs 1, 3, 11, and 13. |
| **YARA Synthesis Engine** | Generator | `VALID` | **100%** | Synthesized valid YARA rule with string & hex patterns. |

---

## Test Suite Performance

- **Total Automated Pytest Cases**: **58 tests**
- **Test Execution Time**: $\sim 7.6\text{ seconds}$
- **Coverage**:
  - `test_c_engine.py`: Native C parity, Shannon entropy bounds, triage parsing.
  - `test_classifier.py`: EMBER features, model probability, Linux ELF bypass.
  - `test_web.py`: FastAPI endpoints, health check, report streaming.
  - `test_triage.py`: Magic byte sniffing, entropy thresholds.
  - `test_reasoning.py`: Attributions, YARA rule generation.

---

## Related Notes
- [[Runbook & Commands|Runbook & Commands]]
- [[02 - Architecture & Agents/Multi-Agent Pipeline|Multi-Agent Pipeline]]
- [[05 - Machine Learning/Verdict Fusion Logic|Verdict Fusion Logic]]
