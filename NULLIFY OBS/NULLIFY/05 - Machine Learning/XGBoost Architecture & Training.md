---
tags:
  - machine-learning
  - xgboost
  - training
  - ember
title: "XGBoost Architecture & Training"
date: 2026-09-13
---

# 🌲 XGBoost Architecture & Training

The machine learning core of Nullify is an **XGBoost (Extreme Gradient Boosting)** classifier trained on 500,000 balanced samples from the [[03 - Data & Intelligence/EMBER 2017 Dataset|EMBER 2017 v2]] dataset.

---

## Model Hyperparameters

The model configuration is stored in `models/malware_xgb.meta.json`:

```json
{
  "n_estimators": 300,
  "max_depth": 8,
  "learning_rate": 0.1,
  "objective": "binary:logistic",
  "tree_method": "hist",
  "eval_metric": "logloss"
}
```

---

## Evaluation Metrics (Test Set)

- **Accuracy**: **99.46%**
- **Precision**: **99.60%** (Extremely low false positives)
- **Recall**: **99.31%** (Detects over 99.3% of all malware)
- **False Positive Rate (FPR)**: **0.39%** ($< 0.4\%$)

---

## Local Training Pipeline

The repository includes scripts to vectorize and train models locally:

```bash
# 1. Vectorize raw EMBER JSONL records
uv run python scripts/vectorize_ember.py \
    --input datasets/ember/ \
    --output datasets/ember/ember_vectors.npz

# 2. Train the XGBoost model
uv run python scripts/train_ember_xgb.py \
    --vectors datasets/ember/ember_vectors.npz \
    --out models/malware_xgb.json
```

---

## Related Notes
- [[Verdict Fusion Logic|Verdict Fusion Logic]]
- [[Google Colab GPU Training|Google Colab GPU Training]]
- [[02 - Architecture & Agents/Agent - Classifier|Agent 5: Classifier]]
- [[03 - Data & Intelligence/EMBER 2017 Dataset|EMBER 2017 Dataset]]
