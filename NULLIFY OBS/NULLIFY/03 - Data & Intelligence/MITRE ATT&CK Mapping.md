---
tags:
  - mitre
  - attack
  - tactics
  - cybersecurity
title: "MITRE ATT&CK Mapping"
date: 2026-09-13
---

# 🗺️ MITRE ATT&CK Framework Mapping

Nullify maps every observed static indicator, behavioral pattern, and log event to standardized **MITRE ATT&CK Enterprise Matrix** techniques.

---

## Primary Techniques Detected

| Technique ID | Technique Name | Detection Trigger |
| :--- | :--- | :--- |
| **T1027** | Obfuscated/Packed Information | High Shannon entropy ($\ge 7.2$), known packer signatures (`UPX`, `ASPack`). |
| **T1055** | Process Injection | Imports `CreateRemoteThread`, `VirtualAllocEx`, Sysmon Event ID 8. |
| **T1059** | Command & Scripting Interpreter | PowerShell execution, `cmd.exe /c`, script shebangs. |
| **T1112** | Modify Registry | Telemetry Event ID 13 altering startup run keys. |
| **T1486** | Data Encrypted for Impact | Ransomware bulk file renaming, shadow copy deletion (`vssadmin`). |
| **T1071** | Application Layer Protocol | HTTP/HTTPS C2 beaconing observed during log or sandbox analysis. |
| **T1083** | File and Directory Discovery | Automated enumeration commands (`dir /s`, `whoami`). |

---

## Purpose in Enterprise SOCs
Assigning standardized ATT&CK IDs allows security analysts to immediately incorporate Nullify findings into incident response playbooks, SIEM correlation rules, and threat hunting workflows.

---

## Related Notes
- [[02 - Architecture & Agents/Agent - Reasoning|Agent 6: Reasoning]]
- [[Sysmon & Event Telemetry|Sysmon & Event Telemetry]]
- [[YARA Synthesis|YARA Synthesis]]
