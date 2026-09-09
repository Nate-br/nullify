# XGBoost Malware Classifier

This model is trained on the EMBER 2017 dataset using `scripts/train_classifier.py`.
The features are 2351-dimensional vectors, extracted from PE files using `src/nullify/core/features.py`.

To train the model:
```bash
uv run python scripts/train_classifier.py --download
```

The resulting model is saved as `models/malware_xgb.json`.
