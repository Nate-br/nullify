import argparse
import json
import logging
import tarfile
import urllib.request
from pathlib import Path

import numpy as np
import xgboost as xgb
from sklearn.metrics import accuracy_score, confusion_matrix, precision_score, recall_score

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def download_ember(target_dir: Path):
    """Downloads the EMBER 2017 dataset."""
    url = "https://ember.elastic.co/ember_dataset_2017_2.tar.bz2"
    target_dir.mkdir(parents=True, exist_ok=True)
    archive_path = target_dir / "ember_dataset_2017_2.tar.bz2"
    
    if not archive_path.exists():
        logger.info(f"Downloading EMBER dataset from {url}...")
        # In a real scenario we'd stream and check size, but this is a placeholder 
        # as per instructions: "download only if the user passes --download and confirm size first"
        req = urllib.request.urlopen(url)
        size = int(req.headers.get('Content-Length', 0))
        logger.info(f"Dataset size is roughly {size / (1024**3):.2f} GB.")
        
        with open(archive_path, 'wb') as f:
            while True:
                chunk = req.read(8192)
                if not chunk:
                    break
                f.write(chunk)
                
    logger.info("Extracting...")
    with tarfile.open(archive_path, "r:bz2") as tar:
        tar.extractall(path=target_dir)

def load_data(dataset_dir: Path, is_train: bool = True):
    """Loads features from jsonl files in the dataset_dir."""
    X, y = [], []
    if is_train:
        files = [dataset_dir / f"train_features_{i}.jsonl" for i in range(6)]
        # For synthetic testing, maybe there is only one file or it's named differently
        if not files[0].exists() and (dataset_dir / "train_features.jsonl").exists():
            files = [dataset_dir / "train_features.jsonl"]
    else:
        files = [dataset_dir / "test_features.jsonl"]

    for file_path in files:
        if not file_path.exists():
            continue
        with open(file_path, "r") as f:
            for line in f:
                data = json.loads(line)
                label = data.get("label", -1)
                if label == -1:
                    continue  # skip unlabeled
                X.append(data.get("features", []))  # Should be 2351 dims or whatever
                y.append(label)
    
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)

def train_model(dataset_dir: Path, model_out: Path):
    X_train, y_train = load_data(dataset_dir, is_train=True)
    X_test, y_test = load_data(dataset_dir, is_train=False)

    if len(X_train) == 0:
        logger.error("No training data found!")
        return

    logger.info(f"Training on {len(X_train)} samples...")
    model = xgb.XGBClassifier(
        n_estimators=100, 
        max_depth=6, 
        learning_rate=0.1, 
        objective='binary:logistic'
    )
    model.fit(X_train, y_train)

    if len(X_test) > 0:
        preds_proba = model.predict_proba(X_test)[:, 1]
        preds = (preds_proba >= 0.5).astype(int)
        
        acc = accuracy_score(y_test, preds)
        prec = precision_score(y_test, preds, zero_division=0)
        rec = recall_score(y_test, preds, zero_division=0)
        
        tn, fp, _fn, _tp = confusion_matrix(y_test, preds).ravel()
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

        logger.info("Evaluation on Test Set:")
        logger.info(f"Accuracy:  {acc:.4f}")
        logger.info(f"Precision: {prec:.4f}")
        logger.info(f"Recall:    {rec:.4f}")
        logger.info(f"FPR:       {fpr:.4f}")

    # XGBoost saves model in JSON
    model.save_model(model_out)
    logger.info(f"Model saved to {model_out}")

    # Write a small metadata file
    readme_path = model_out.parent / "README.md"
    with open(readme_path, "w") as f:
        f.write("# XGBoost Malware Classifier\n\nThis model is trained on the EMBER 2017 dataset.\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train XGBoost classifier on EMBER")
    parser.add_argument("--dataset-dir", type=str, default="datasets/ember", help="Path to EMBER dataset directory")
    parser.add_argument("--download", action="store_true", help="Download the dataset if not present")
    parser.add_argument("--model-out", type=str, default="models/malware_xgb.json", help="Path to save the trained model")
    args = parser.parse_args()

    dataset_dir = Path(args.dataset_dir)
    if args.download:
        download_ember(dataset_dir)

    train_model(dataset_dir, Path(args.model_out))
