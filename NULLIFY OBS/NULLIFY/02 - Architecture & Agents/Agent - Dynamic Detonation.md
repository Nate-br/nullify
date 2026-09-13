---
tags:
  - agent
  - dynamic-analysis
  - sandbox
  - capev2
title: "Agent 3: Dynamic Detonation Agent"
date: 2026-09-13
---

# 💥 Agent 3: Dynamic Detonation Agent

The **Dynamic Detonation Agent** oversees the execution of suspicious binaries in an isolated sandbox environment.

---

## Safety Boundary & Execution Policy

> [!danger] Host Safety Contract
> - **Zero Host Execution**: Samples are never executed directly on the host machine.
> - **Strictly Opt-In**: Dynamic execution is gated by the `--deep` CLI flag or the `Deep` toggle in the Web UI.
> - **External Sandbox Target**: Communicates over a private REST API with an external **CAPEv2 Sandbox** instance running isolated Windows VM guests.

---

## Behavioral Observations Collected

When detonated in the sandbox, the agent observes and aggregates:
1. **Process Trees & Spawning**: Detects execution of `powershell.exe -enc`, `cmd.exe /c`, or `vssadmin.exe delete shadows` ([[03 - Data & Intelligence/MITRE ATT&CK Mapping|MITRE T1486]]).
2. **File System Mutations**: Tracks dropped executables in `%TEMP%` or `%APPDATA%`, and mass file renaming (ransomware file extensions like `.locked`).
3. **Registry Persistence**: Detects writes to `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`.
4. **Network Telemetry**: Captures DNS queries, HTTP POST beacons, and raw IP connections to Command and Control (C2) servers.

---

## Related Notes
- [[Multi-Agent Pipeline|Multi-Agent Pipeline]]
- [[Agent - Log Correlation|Agent 4: Log Correlation]]
- [[Agent - Reasoning|Agent 6: Reasoning]]
