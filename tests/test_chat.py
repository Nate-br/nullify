from unittest.mock import patch

from fastapi.testclient import TestClient

from nullify.interfaces.web import chat
from nullify.interfaces.web.backend import app

client = TestClient(app)

def test_chat_unavailable_503(tmp_path):
    with patch("nullify.interfaces.web.chat.MODELS_DIR", tmp_path):
        response = client.post("/api/chat", json={"message": "hello", "include_context": False})
        assert response.status_code == 503
        assert "chat model not available" in response.json()["error"]

def test_chat_success_with_context(monkeypatch):
    class FakeEngine:
        def available(self):
            return True
            
        def generate(self, messages):
            assert len(messages) >= 3
            assert messages[0]["role"] == "system"
            assert messages[1]["role"] == "user"
            assert "SCAN CONTEXT" in messages[1]["content"]
            assert messages[2]["role"] == "user"
            assert messages[2]["content"] == "explain"
            return "ok"
            
    monkeypatch.setattr(chat, "ChatEngine", FakeEngine)
    monkeypatch.setattr(chat, "last_report", {
        "verdict": "malicious",
        "confidence": 0.99,
        "malware_type": "trojan",
        "mitre_ids": ["T1059"],
        "agents": [
            {"findings": [{"title": "Suspicious import", "severity": "high"}]}
        ]
    })
    
    response = client.post("/api/chat", json={"message": "explain", "include_context": True})
    assert response.status_code == 200
    assert response.json() == {"reply": "ok"}
    
def test_chat_success_no_context(monkeypatch):
    class FakeEngine:
        def available(self):
            return True
            
        def generate(self, messages):
            assert len(messages) == 2
            assert messages[0]["role"] == "system"
            assert messages[1]["role"] == "user"
            assert messages[1]["content"] == "explain"
            return "ok"
            
    monkeypatch.setattr(chat, "ChatEngine", FakeEngine)
    monkeypatch.setattr(chat, "last_report", None)
    
    response = client.post("/api/chat", json={"message": "explain", "include_context": False})
    assert response.status_code == 200
    assert response.json() == {"reply": "ok"}
