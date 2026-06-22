from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "model" in data


def test_clear_session():
    response = client.delete("/api/v1/chat/sessions/test-session")
    assert response.status_code == 200
    assert response.json()["session_id"] == "test-session"
