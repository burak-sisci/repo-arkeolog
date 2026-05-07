"""FastAPI endpoint entegrasyon testleri."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_analyze_invalid_url(client):
    resp = client.post("/api/analyze", json={"repo_url": "not-a-url"})
    # Should fail at validation or return error
    assert resp.status_code in (400, 422)


def test_analysis_not_found(client):
    resp = client.get("/api/analysis/nonexistent-id")
    assert resp.status_code == 404
