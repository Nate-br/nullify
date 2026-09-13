# Nullify Google Colab Model Training

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/Nate-br/nullify/blob/master/notebooks/train_nullify_colab.ipynb)

This directory contains the automated, GPU-accelerated Google Colab training notebook for Nullify's **EMBER 2,381-dimensional XGBoost Malware Classification Model**.

---

## 🚀 How to Run in Google Colab

1. Click the **"Open In Colab"** badge above (or navigate to [Google Colab](https://colab.research.google.com) and open `notebooks/train_nullify_colab.ipynb` from GitHub).
2. Under the Colab menu, go to **Runtime** $\to$ **Change runtime type**, and select **T4 GPU** (or A100 GPU if available).
3. Click **Runtime** $\to$ **Run all** (or `Ctrl + F9`).
4. The notebook will automatically:
   - Configure GPU acceleration (`device="cuda"`).
   - Ingest training vectors across 2,381 features.
   - Train XGBoost with stratified validation and early stopping.
   - Plot Confusion Matrix and ROC Curves with AUC score.
   - Trigger a direct browser download of `malware_xgb.json` and `malware_xgb.meta.json`.

---

## 📦 Updating Nullify with Your Retrained Model

Once downloaded, copy the files into your local Nullify repository:

```bash
cp ~/Downloads/malware_xgb.json models/malware_xgb.json
cp ~/Downloads/malware_xgb.meta.json models/malware_xgb.meta.json
```

Verify that Nullify's test suite passes with your new model:

```bash
uv run pytest
```
