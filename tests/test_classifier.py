
import numpy as np
import pytest

from nullify.core.agents.classifier import ClassificationAgent, classify
from nullify.core.models import FileTarget, ScanMode, Verdict

try:
    import xgboost as xgb
    XGB_AVAILABLE = True
except ImportError:
    XGB_AVAILABLE = False


@pytest.fixture
def dummy_model_path(tmp_path):
    if not XGB_AVAILABLE:
        pytest.skip("XGBoost not installed")
        
    model_out = tmp_path / "malware_xgb.json"
    
    # Train tiny model on 200 synthetic rows
    np.random.seed(42)
    X_train = np.random.rand(200, 2351).astype(np.float32)
    # Give some predictable pattern: if feature 0 > 0.5, label 1, else 0
    y_train = (X_train[:, 0] > 0.5).astype(int)
    
    model = xgb.XGBClassifier(n_estimators=10, max_depth=3, objective='binary:logistic')
    model.fit(X_train, y_train)
    model.save_model(model_out)
    
    return model_out


@pytest.fixture
def dummy_target(tmp_path):
    target_file = tmp_path / "dummy.exe"
    target_file.write_bytes(b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff\x00\x00\xb8\x00\x00\x00\x00\x00\x00\x00\x40\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00")
    return FileTarget(path=str(target_file))


def test_classifier_fallback(dummy_target):
    """Test that the heuristic fallback still works when no model exists."""
    evidence = {
        "reputation": {"known_malicious": True},
        "type_votes": {"trojan": 3},
        "packed": True
    }
    
    # Test pure function
    result = classify(evidence)
    assert result["verdict"] == Verdict.MALICIOUS
    assert result["malware_type"] == "trojan"
    assert result["engine"] == "heuristic-phase0"
    
    # Test agent
    agent = ClassificationAgent(config={"evidence": evidence}, model_path="non_existent_model.json")
    agent_res = agent.analyze(dummy_target, ScanMode.STATIC_ONLY)
    
    assert agent_res.data["engine"] == "heuristic-phase0"
    assert agent_res.data["verdict"] == "malicious"


def test_classifier_xgboost(dummy_target, dummy_model_path):
    """Test that the XGBoost model works end-to-end."""
    evidence = {
        "reputation": {},
        "type_votes": {},
        "packed": False
    }
    
    agent = ClassificationAgent(config={"evidence": evidence}, model_path=dummy_model_path)
    assert agent.model is not None
    
    agent_res = agent.analyze(dummy_target, ScanMode.STATIC_ONLY)
    
    assert agent_res.data["engine"] == "xgboost-ember"
    assert "score" in agent_res.data
    assert "verdict" in agent_res.data

