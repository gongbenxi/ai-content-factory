"""runs API 测试"""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from app.main import app
    return TestClient(app)


def test_create_run(client):
    with patch("app.api.runs.start_run_background", new_callable=AsyncMock):
        resp = client.post("/api/runs", json={"user_request": "测试", "mock": True})
    assert resp.status_code == 200
    data = resp.json()
    assert "run_id" in data
    assert data["status"] == "drafting"
