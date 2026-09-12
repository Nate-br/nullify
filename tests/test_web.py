"""Tests for the web UI backend."""

import pytest
from fastapi.testclient import TestClient

from nullify.interfaces.web.backend import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_scan_benign(client, benign_file):
    response = client.post("/api/scan", json={"path": str(benign_file.path)})
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] == "benign"

    assert "mitre_ids" in data

    agent_names = [a["agent"] for a in data["agents"]]
    assert "Triage" in agent_names
    assert "Static" in agent_names
    assert "Classifier" in agent_names


def test_samples_endpoint(client):
    response = client.get("/api/samples")
    assert response.status_code == 200
    data = response.json()
    assert "samples" in data
    assert len(data["samples"]) >= 3
    sample_ids = [s["id"] for s in data["samples"]]
    assert "trojan" in sample_ids
    assert "ransomware" in sample_ids
    assert "benign" in sample_ids


def test_generate_rule_endpoint(client):
    response = client.post(
        "/api/generate-rule",
        json={
            "findings": [{"title": "CreateRemoteThread", "detail": "Suspicious import"}],
            "imports": ["CreateRemoteThread", "URLDownloadToFile"],
            "family": "Trojan",
            "name_hint": "TestSample",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "rule" in data
    assert "rule Gen_Trojan" in data["rule"]


def test_upload_endpoint(client, tmp_path):
    sample_path = tmp_path / "test_sample.exe"
    sample_path.write_bytes(b"MZ" + b"\x00" * 128)
    with open(sample_path, "rb") as fh:
        response = client.post(
            "/api/upload",
            files={"file": ("test_sample.exe", fh, "application/octet-stream")},
        )
    assert response.status_code == 200
    data = response.json()
    assert "verdict" in data
    assert "confidence" in data
