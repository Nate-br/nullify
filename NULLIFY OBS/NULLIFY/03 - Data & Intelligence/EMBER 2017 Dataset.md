---
tags:
  - dataset
  - ember
  - machine-learning
  - features
title: "The EMBER 2017 v2 Dataset & 2,381 Features"
date: 2026-09-13
---

# 📊 The EMBER 2017 v2 Dataset & 2,381 Features

The **EMBER (Elastic Malware Benchmark for Empowering Researchers)** dataset was created by Elastic Security and Endgame. It serves as the standard benchmark for training machine learning models on Windows PE binaries.

---

## Dataset Scale
- **Total Binaries**: **1,100,000+** Windows executables
- **Training Set**: 900,000 binaries
- **Test Set**: 200,000 binaries
- **Feature Dimensionality**: **2,381 features per binary**

---

## Breakdown of the 2,381 Feature Dimensions

```
┌────────────────────────────────────────────────────────────────────────┐
│                        EMBER 2,381-DIM MATRIX                          │
├────────────────────────────┬───────┬───────────────────────────────────┤
│ Feature Block              │ Dims  │ Core Measurement                  │
├────────────────────────────┼───────┼───────────────────────────────────┤
│ ByteHistogram              │ 256   │ Frequency counts of bytes 0x00..FF│
│ ByteEntropyHistogram       │ 256   │ 16x16 sliding-window entropy      │
│ StringExtractor            │ 104   │ Length, printable dist, URLs, MZ  │
│ GeneralFileInfo            │ 10    │ Size, exports, imports, TLS, syms │
│ HeaderFileInfo             │ 62    │ COFF machine, timestamp, OS/link  │
│ SectionInfo                │ 255   │ Section counts, entropy, W+X flags│
│ ImportsInfo                │ 1,280 │ Hashed library names & API calls  │
│ ExportsInfo                │ 128   │ Hashed export symbols             │
│ DataDirectories            │ 30    │ Virtual sizes & RVAs for 15 dirs  │
├────────────────────────────┼───────┼───────────────────────────────────┤
│ Total Feature Dimensions   │ 2,381 │                                   │
└────────────────────────────┴───────┴───────────────────────────────────┘
```

---

## Native C Acceleration

In Nullify, computing the sliding-window matrix (`ByteEntropyHistogram`) and ASCII heuristics (`StringExtractor`) is accelerated by [[04 - Native C Engine/Native C-Core Accelerator|Native C]] in `src/c/ember_fast.c`, speeding up feature extraction by **5x to 7x** with 100% numerical parity.

---

## Related Notes
- [[02 - Architecture & Agents/Agent - Classifier|Agent 5: Classifier]]
- [[04 - Native C Engine/Native C-Core Accelerator|Native C Engine]]
- [[05 - Machine Learning/XGBoost Architecture & Training|XGBoost Architecture]]
- [[05 - Machine Learning/Google Colab GPU Training|Google Colab GPU Training]]
