---
tags:
  - agent
  - static-analysis
  - pefile
  - yara
title: "Agent 2: Static Analysis Agent"
date: 2026-09-13
---

# 🧬 Agent 2: Static Analysis Agent

The **Static Analysis Agent** dissects the internal anatomy of binary files without executing them. It parses structural tables, identifies suspicious memory permissions, flags dangerous Windows API imports, and matches behavioral [[03 - Data & Intelligence/YARA Synthesis|YARA rules]].

---

## Core Analysis Functions

### 1. Section Structure & Permissions
- Inspects section names (`.text`, `.data`, `.rsrc`, `.reloc`).
- Flags anomalous sections created by packers (e.g. `UPX0`, `UPX1`, `ASPack`, `MPRESS`, `PEC2`).
- Identifies **W+X sections** (sections marked both `MEM_WRITE` and `MEM_EXECUTE`), which are hallmark indicators of self-modifying code or shellcode injection ([[03 - Data & Intelligence/MITRE ATT&CK Mapping|MITRE T1055]]).
- Computes section virtual size vs. raw disk size ratio. If $\text{VirtualSize} \gg \text{RawSize}$, it detects unpacked memory staging.

### 2. Suspicious Windows API Import Inspection
Extracts imported symbols via `pefile` and flags known malicious capabilities:
- **Process Injection**: `VirtualAllocEx`, `WriteProcessMemory`, `CreateRemoteThread`, `QueueUserAPC`.
- **Evasion / Unhooking**: `NtProtectVirtualMemory`, `SetThreadContext`.
- **Persistence**: `RegSetValueExA`, `CreateServiceA`.
- **Credential Access**: `MiniDumpWriteDump`, `OpenProcess`, `LsaEnumerateLogonSessions`.

### 3. Behavioral YARA Rules
Scans the binary against compiled behavioral YARA rules detecting ransomware extensions, C2 domain patterns, and trojan markers.

---

## Related Notes
- [[Multi-Agent Pipeline|Multi-Agent Pipeline]]
- [[Agent - Triage|Agent 1: Triage]]
- [[03 - Data & Intelligence/YARA Synthesis|YARA Synthesis]]
