"""Vectorize the EMBER 2017 dataset into a compact .npz for training.

Single streaming pass over the train shards. Because EMBER 2017 shards are
label-grouped (early shards benign, malicious concentrated later), rows are
vectorized lazily against per-class caps — benign rows beyond the cap are
skipped without paying the vectorization cost.

Usage:
    uv run python scripts/vectorize_ember.py \
        --shard-dir datasets/ember/ember_2017_2 \
        --out datasets/ember/ember_vectors.npz \
        --max-benign 250000 --max-malicious 250000
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from nullify.core.ember_features import EMBER_V2_DIM, ember_feature_vector_from_raw


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--shard-dir", type=Path, default=Path("datasets/ember/ember_2017_2"))
    ap.add_argument("--out", type=Path, default=Path("datasets/ember/ember_vectors.npz"))
    ap.add_argument("--max-benign", type=int, default=250_000)
    ap.add_argument("--max-malicious", type=int, default=250_000)
    args = ap.parse_args()

    shards = sorted(args.shard_dir.glob("train_features_*.jsonl"))
    if not shards:
        print(f"ERROR: no train_features_*.jsonl under {args.shard_dir}", file=sys.stderr)
        return 1

    counts = {0: 0, 1: 0}
    skipped = {-1: 0, 0: 0, 1: 0}
    t0 = time.time()
    total = 0

    # Preallocate once (500K x 2381 float32 = 4.8 GB) — no list-append + vstack
    # double copy, which OOM-killed the first attempt on a 14 GB box.
    X = np.empty((args.max_benign + args.max_malicious, EMBER_V2_DIM), dtype=np.float32)
    y = np.empty(args.max_benign + args.max_malicious, dtype=np.float32)
    n = 0

    for shard in shards:
        print(f"[{time.time() - t0:7.0f}s] {shard.name} ...", flush=True)
        with shard.open("r", encoding="utf-8") as fh:
            for line in fh:
                total += 1
                rec = json.loads(line)
                label = rec.get("label", -1)
                if label not in (0, 1):
                    skipped[-1] += 1
                    continue
                if label == 0 and counts[0] >= args.max_benign:
                    skipped[0] += 1
                    continue
                if label == 1 and counts[1] >= args.max_malicious:
                    skipped[1] += 1
                    continue
                X[n] = ember_feature_vector_from_raw(rec)
                y[n] = label
                n += 1
                counts[label] += 1
        print(f"    kept so far: benign={counts[0]} malicious={counts[1]}", flush=True)

    X = X[:n]
    y = y[:n]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    # Raw .npy pairs (not .npz): .npy supports mmap in the trainer, .npz does not.
    x_path = args.out.with_name(args.out.stem + "_X.npy")
    y_path = args.out.with_name(args.out.stem + "_y.npy")
    np.save(x_path, X)
    np.save(y_path, y)

    print(f"\nrows kept: {len(y)} (benign={counts[0]}, malicious={counts[1]})")
    print(f"skipped: unlabeled={skipped[-1]}, benign-over-cap={skipped[0]}, mal-over-cap={skipped[1]}")
    print(f"total lines scanned: {total}")
    print(f"dims: {X.shape[1]}")
    print(f"saved: {x_path} ({x_path.stat().st_size / 1e6:.0f} MB) + {y_path.name}, "
          f"{time.time() - t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
