"""Train the Nullify XGBoost malware classifier on EMBER 2017 vectors.

Loads the .npz produced by vectorize_ember.py, splits train/test, trains
XGBoost, reports accuracy/precision/recall/FPR, and saves the model plus a
metadata sidecar to models/.

Usage:
    uv run python scripts/train_ember_xgb.py \
        --vectors datasets/ember/ember_vectors.npz \
        --out models/malware_xgb.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main() -> int:
    import xgboost as xgb
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        precision_score,
        recall_score,
    )

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--vectors", type=Path, default=Path("datasets/ember/ember_vectors.npz"))
    ap.add_argument("--out", type=Path, default=Path("models/malware_xgb.json"))
    ap.add_argument("--test-size", type=float, default=0.1)
    ap.add_argument("--n-estimators", type=int, default=300)
    ap.add_argument("--max-depth", type=int, default=8)
    ap.add_argument("--learning-rate", type=float, default=0.1)
    args = ap.parse_args()

    x_path = args.vectors.with_name(args.vectors.stem + "_X.npy")
    y_path = args.vectors.with_name(args.vectors.stem + "_y.npy")
    if not x_path.exists():
        print(f"ERROR: {x_path} not found — run vectorize_ember.py first", file=sys.stderr)
        return 1

    # mmap the raw .npy pair (written by vectorize_ember.py) — only the shuffle
    # result is materialized, one 4.8 GB copy at float32.
    X_all = np.load(x_path, mmap_mode="r")
    y_all = np.load(y_path, mmap_mode="r")
    idx = np.arange(X_all.shape[0])
    np.random.seed(42)
    np.random.shuffle(idx)
    X = np.asarray(X_all[idx], dtype=np.float32)
    y = np.asarray(y_all[idx], dtype=np.float32)
    print(f"loaded {X.shape[0]} rows x {X.shape[1]} dims "
          f"(malicious={int(y.sum())}, benign={int((y == 0).sum())})", flush=True)

    n_test = max(1, int(X.shape[0] * args.test_size))
    X_te, y_te = X[:n_test], y[:n_test]
    X_tr, y_tr = X[n_test:], y[n_test:]
    print(f"train={len(y_tr)} test={len(y_te)}", flush=True)

    model = xgb.XGBClassifier(
        n_estimators=args.n_estimators,
        max_depth=args.max_depth,
        learning_rate=args.learning_rate,
        objective="binary:logistic",
        eval_metric="logloss",
        tree_method="hist",
        n_jobs=4,
    )
    t0 = time.time()
    model.fit(X_tr, y_tr)
    print(f"trained in {time.time() - t0:.0f}s", flush=True)

    proba = model.predict_proba(X_te)[:, 1]
    preds = (proba >= 0.5).astype(int)
    acc = accuracy_score(y_te, preds)
    prec = precision_score(y_te, preds, zero_division=0)
    rec = recall_score(y_te, preds, zero_division=0)
    tn, fp, _fn, _tp = confusion_matrix(y_te, preds).ravel()
    fpr = fp / (fp + tn) if (fp + tn) else 0.0

    print(f"accuracy={acc:.4f} precision={prec:.4f} recall={rec:.4f} FPR={fpr:.4f}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    model.save_model(args.out)

    meta = {
        "trained_at": datetime.now(UTC).isoformat(),
        "dataset": "EMBER 2017 v2 (feature_version=2, 2381 dims)",
        "rows": int(X.shape[0]),
        "malicious": int(y.sum()),
        "benign": int((y == 0).sum()),
        "test_size": args.test_size,
        "params": {
            "n_estimators": args.n_estimators,
            "max_depth": args.max_depth,
            "learning_rate": args.learning_rate,
            "objective": "binary:logistic",
            "tree_method": "hist",
        },
        "metrics": {
            "accuracy": round(float(acc), 4),
            "precision": round(float(prec), 4),
            "recall": round(float(rec), 4),
            "fpr": round(float(fpr), 4),
        },
        "thresholds": {"malicious": 0.85, "suspicious": 0.4},
        "feature_extractor": "src/nullify/core/ember_features.py (vendored, pefile-backed)",
    }
    meta_path = args.out.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2))
    print(f"saved model: {args.out}")
    print(f"saved metadata: {meta_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
