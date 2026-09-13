---
tags:
  - agent
  - triage
  - c-core
title: "Agent 1: Triage Agent"
date: 2026-09-13
---

# 🔍 Agent 1: Triage Agent

The **Triage Agent** is the gatekeeper of the Nullify pipeline. It executes first, performing rapid, low-overhead filtering to classify file types, detect packing/encryption, and compute cryptographic signatures.

---

## Capabilities & Implementation

- **Language**: Accelerated via [[04 - Native C Engine/Native C-Core Accelerator|Native C Engine]] (`libnullify.so` / `pe_elf.c` / `hash.c`).
- **Speed**: $< 15\text{ ms}$ on multi-megabyte payloads.

### 1. Magic Byte Sniffing
Instead of trusting file extensions (which attackers easily falsify), Triage inspects raw magic headers:
- `b"MZ"` $\to$ Windows PE (Portable Executable)
- `b"\x7fELF"` $\to$ Linux ELF binary
- `b"#!"` $\to$ Script / Shebang payload

### 2. Shannon Entropy Calculation
Measures the randomness of byte distribution on a scale of $0.0 \text{ to } 8.0$:
$$H(X) = -\sum_{i=0}^{255} P(x_i) \log_2 P(x_i)$$
- **Entropy $< 6.8$**: Standard compiled code / plaintext.
- **Entropy $\ge 7.2$**: Elevated entropy — flagged as `PACKED / OBFUSCATED` ([[03 - Data & Intelligence/MITRE ATT&CK Mapping|MITRE T1027]]).
- **Entropy $\ge 7.8$**: Very high entropy — indicates dense encryption (e.g. Ransomware payload or encrypted shellcode).

### 3. Native Cryptographic Hashes
Computes **MD5** and **SHA-256** checksums natively in C without external OpenSSL library dependencies.

---

## Related Notes
- [[Multi-Agent Pipeline|Multi-Agent Pipeline]]
- [[04 - Native C Engine/Native C-Core Accelerator|Native C-Core Accelerator]]
- [[Agent - Static Analysis|Agent 2: Static Analysis]]
