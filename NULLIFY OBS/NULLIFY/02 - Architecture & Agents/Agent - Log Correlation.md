---
tags:
  - agent
  - sysmon
  - evtx
  - telemetry
title: "Agent 4: Log Correlation Agent"
date: 2026-09-13
---

# 📜 Agent 4: Log Correlation Agent

The **Log Correlation Agent** inspects endpoint telemetry logs to identify malicious activity occurring across an operating system.

---

## Supported Log Formats
- Microsoft Sysmon JSONL exports (`.jsonl`)
- Windows Security Event Logs (`.evtx`)

---

## Monitored Sysmon Event IDs

```
┌──────────┬───────────────────────┬──────────────────────────────────────────┐
│ Event ID │ Event Name            │ Threat Intelligence Detection            │
├──────────┼───────────────────────┼──────────────────────────────────────────┤
│ ID 1     │ Process Creation      │ Encoded PowerShell, LOLBins (certutil)   │
│ ID 3     │ Network Connection    │ Outbound C2 beacons, suspicious ports    │
│ ID 7     │ Image Loaded          │ Unsigned DLLs, reflective DLL injection  │
│ ID 8     │ CreateRemoteThread    │ Process injection, Cobalt Strike beacons │
│ ID 11    │ File Create           │ Dropped ransom notes, payloads in %TEMP% │
│ ID 13    │ Registry Value Set    │ Autorun persistence keys                 │
└──────────┴───────────────────────┴──────────────────────────────────────────┘
```

---

## Behavioral Correlation

The agent links individual events into cohesive threat chains:
$$\text{Outlook.exe} \to \text{cmd.exe} \to \text{powershell.exe} \to \text{vssadmin.exe}$$
Detecting this parent-child sequence triggers a high-severity finding for **Ransomware Staging** mapped to [[03 - Data & Intelligence/MITRE ATT&CK Mapping|MITRE T1059]].

---

## Related Notes
- [[Multi-Agent Pipeline|Multi-Agent Pipeline]]
- [[03 - Data & Intelligence/Sysmon & Event Telemetry|Sysmon & Event Telemetry]]
- [[Agent - Reasoning|Agent 6: Reasoning]]
