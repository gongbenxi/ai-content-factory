"""Run lifecycle API coverage."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.services.memory_store import EVENTS, RUNS


def test_create_run_rejects_unknown_style_without_memory_fallback():
    from app.main import app

    RUNS.clear()
    EVENTS.clear()
    client = TestClient(app)

    with (
        patch("app.api.runs._style_exists", new=AsyncMock(return_value=False)),
        patch("app.api.runs.start_run_background", new=AsyncMock()),
    ):
        resp = client.post("/api/runs", json={"user_request": "测试创建链路", "style_id": "missing-style", "mock": True})

    assert resp.status_code == 422
    assert resp.json()["detail"]["code"] == "STYLE_NOT_FOUND"
    assert RUNS == {}


def test_create_run_does_not_fallback_to_memory_when_db_write_fails():
    from app.main import app

    RUNS.clear()
    EVENTS.clear()
    client = TestClient(app)

    with (
        patch("app.api.runs._create_run_db", new=AsyncMock(side_effect=RuntimeError("db down"))),
        patch("app.api.runs.start_run_background", new=AsyncMock()),
    ):
        resp = client.post("/api/runs", json={"user_request": "测试创建链路", "mock": True})

    assert resp.status_code == 500
    assert resp.json()["detail"]["code"] == "RUN_DB_WRITE_FAILED"
    assert RUNS == {}


def test_create_run_persists_before_starting_worker():
    from app.main import app

    client = TestClient(app)
    create_db = AsyncMock()
    worker = AsyncMock()

    with (
        patch("app.api.runs._style_exists", new=AsyncMock(return_value=True)),
        patch("app.api.runs._create_run_db", new=create_db),
        patch("app.api.runs.start_run_background", new=worker),
    ):
        resp = client.post("/api/runs", json={"user_request": "测试创建链路", "style_id": "default", "mock": True})

    assert resp.status_code == 200
    create_db.assert_awaited_once()
    assert resp.json()["status"] == "drafting"


def test_failed_run_status_and_events_are_visible_from_memory(monkeypatch):
    from app.main import app
    from app.services.memory_store import append_event, upsert_run

    monkeypatch.setenv("ACF_ENABLE_MEMORY_FALLBACK", "1")
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
