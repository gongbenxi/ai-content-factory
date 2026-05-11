"""Run lifecycle API coverage."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.services.memory_store import EVENTS, RUNS


def test_create_run_can_be_read_back_from_memory():
    from app.main import app

    RUNS.clear()
    EVENTS.clear()
    client = TestClient(app)

    with (
        patch("app.api.runs._try_db_write_run", new=AsyncMock(return_value=False)),
        patch("app.api.runs.start_run_background", new=AsyncMock()),
    ):
        resp = client.post("/api/runs", json={"user_request": "测试创建链路", "mock": True})

    assert resp.status_code == 200
    run_id = resp.json()["run_id"]

    detail = client.get(f"/api/runs/{run_id}").json()
    assert detail["run_id"] == run_id
    assert detail["status"] == "drafting"
    assert detail["user_request"] == "测试创建链路"


def test_failed_run_status_and_events_are_visible_from_memory():
    from app.main import app
    from app.services.memory_store import append_event, upsert_run

    RUNS.clear()
    EVENTS.clear()
    client = TestClient(app)

    run_id = "failure-run"
    upsert_run(run_id, user_request="失败可见性", status="failed", error="boom")
    append_event(run_id, "graph.start", {"run_id": run_id})
    append_event(run_id, "graph.error", {"run_id": run_id, "error": "boom"})

    detail = client.get(f"/api/runs/{run_id}").json()
    events = client.get(f"/api/runs/{run_id}/events").json()["events"]

    assert detail["status"] == "failed"
    assert detail["error"] == "boom"
    assert [event["event"] for event in events] == ["graph.start", "graph.error"]
