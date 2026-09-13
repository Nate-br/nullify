---
tags:
  - telemetry
  - sysmon
  - evtx
  - endpoint
title: "Sysmon & Windows Event Telemetry"
date: 2026-09-13
---

# 📡 Sysmon & Windows Event Telemetry

While static file analysis inspects the binary on disk, **endpoint telemetry** reveals what code actually does when it runs on an enterprise endpoint.

---

## The Log Ingestion Engine

Nullify accepts two standard telemetry formats:
1. **Sysmon JSONL Files** (`.jsonl`): Pre-parsed structured event records.
2. **Windows Security Event Logs** (`.evtx`): Binary event log files extracted directly from compromised endpoints.

---

## Key Sysmon Event IDs Evaluated

```
┌──────────┬─────────────────────────┬───────────────────────────────────────────┐
│ Event ID │ Event Description       │ Threat Indicators Tracked                 │
├──────────┼─────────────────────────┼───────────────────────────────────────────┤
│ 1        │ Process Create          │ `CommandLine`, parent process, LOLBins   │
│ 3        │ Network Connection      │ Destination IP, port, C2 beacon intervals │
│ 7        │ Image Loaded            │ Unsigned DLLs loaded into memory space    │
│ 8        │ CreateRemoteThread      │ Cross-process injection (e.g. into lsass) │
│ 11       │ File Create             │ Encrypted file extensions, drop locations │
│ 13       │ Registry Value Set      │ `CurrentVersion\Run` persistence keys     │
└──────────┴─────────────────────────┴───────────────────────────────────────────┘
```

---

## Correlating Telemetry with MITRE ATT&CK

When an event sequence matches known threat behaviors, Nullify automatically tags it:
- `vssadmin.exe delete shadows` $\to$ **[[MITRE ATT&CK Mapping|T1486 (Inhibit System Recovery)]]**
- `powershell.exe -ExecutionPolicy Bypass -enc ...` $\to$ **[[MITRE ATT&CK Mapping|T1059 (Command and Scripting Interpreter)]]**
- `RegSetValueEx` on `RunOnce` $\to$ **[[MITRE ATT&CK Mapping|T1112 (Modify Registry)]]**

---

## Related Notes
- [[02 - Architecture & Agents/Agent - Log Correlation|Agent 4: Log Correlation]]
- [[MITRE ATT&CK Mapping|MITRE ATT&CK Mapping]]
- [[07 - Verification & Runbook/Real-World Evaluation Record|Real-World Evaluation Record]]
