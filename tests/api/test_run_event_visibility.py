"""Runner event visibility coverage."""

import pytest

from app.services.memory_store import EVENTS, RUNS


@pytest.mark.asyncio
async def test_mock_run_emits_core_events_and_persists_draft(monkeypatch):
    from app.workers import runner
    from app.agents import researcher

    RUNS.clear()
    EVENTS.clear()

    async def skip_db(*args, **kwargs):
        return False

    async def fake_search(*args, **kwargs):
        return []

    async def fake_scrape(*args, **kwargs):
        return {"success": False}

    monkeypatch.setattr(runner, "_append_event_db", skip_db)
    monkeypatch.setattr(runner, "_update_run_db", skip_db)
    monkeypatch.setattr(researcher, "web_search", fake_search)
    monkeypatch.setattr(researcher, "scrape_url", fake_scrape)
    monkeypatch.setenv("ACF_ENABLE_CHECKPOINT", "0")

    run_id = "00000000-0000-0000-0000-000000000001"
    request = "外交部介绍特朗普访华安排和中方期待"
    await runner.start_run(run_id, request, mock=True)

    event_types = [event["event"] for event in EVENTS[run_id]]
    stored = RUNS[run_id]

    assert "graph.start" in event_types
    assert "agent.start" in event_types
    assert "writer.token" in event_types
    assert "graph.done" in event_types
    assert any(
        event["event"] == "agent.done" and event["data"].get("usage")
        for event in EVENTS[run_id]
    )
    assert stored["status"] == "done"
    assert stored["draft_md"]
    assert request in stored["draft_md"]
    assert "DeepSeek-V3" not in stored["draft_md"]
    assert stored["total_tokens"] >= 0
