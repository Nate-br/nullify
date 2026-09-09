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
