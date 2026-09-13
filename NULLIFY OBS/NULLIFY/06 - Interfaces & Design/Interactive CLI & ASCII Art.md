---
tags:
  - cli
  - terminal
  - ascii-art
  - typer
title: "Interactive CLI & ASCII Art Experience"
date: 2026-09-13
---

# 💻 Interactive CLI & ASCII Art Experience

The command-line interface provides high-speed workflows for terminal users, scripting, and batch directory scanning.

---

## The Single-Command Interactive Launcher

Instead of forcing users to remember subcommands, running `nullify` with zero arguments launches an interactive console:

```bash
uv run nullify
```

```
███╗   ██╗██╗   ██╗██╗     ██╗     ██╗███████╗██╗   ██╗
████╗  ██║██║   ██║██║     ██║     ██║██╔════╝╚██╗ ██╔╝
██╔██╗ ██║██║   ██║██║     ██║     ██║█████╗   ╚████╔╝ 
██║╚██╗██║██║   ██║██║     ██║     ██║██╔══╝    ╚██╔╝  
██║ ╚████║╚██████╔╝███████╗███████╗██║██║        ██║   
╚═╝  ╚═══╝ ╚═════╝ ╚══════╝╚══════╝╚═╝╚═╝        ╚═╝   
```

---

## Interactive Menu Options

1. `[1] Quick Scan`: Fast static inspection and ML classification.
2. `[2] Deep Detonation Scan`: Opt-in sandboxed dynamic detonation (`--deep`).
3. `[3] Analyze Behavioral Log`: Sysmon and Windows EVTX correlation.
4. `[4] Batch Scan Directory`: Scan an entire directory of files.
5. `[5] Launch Web Console`: Starts local server at `http://127.0.0.1:8000`.
6. `[6] Test Synthetic Demos`: Runs built-in safe fixtures (Trojan, Ransomware, Benign).
7. `[0] Exit`: Exits the console.

---

## Standalone C CLI (`bin/nullify-core`)

For minimal server environments without Python:
```bash
./bin/nullify-core /path/to/binary [--json]
```
Outputs complete triage and hashes in $< 15\text{ ms}$.

---

## Related Notes
- [[Luxury Editorial Web UI|Luxury Editorial Web UI]]
- [[04 - Native C Engine/Native C-Core Accelerator|Native C-Core Accelerator]]
- [[07 - Verification & Runbook/Runbook & Commands|Runbook & Commands]]
