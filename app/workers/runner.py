"""LangGraph driver — 后台运行任务"""

from __future__ import annotations

import asyncio
import time
import uuid
from datetime import datetime

from app.agents.graph import acompile_graph, ContentState
from app.llm.budget import BudgetGuard, BudgetExceeded
from app.services.memory_store import append_event, upsert_run

_RUN_TIMEOUT_SECONDS = 900  # 15 分钟硬超时
_DB_BEST_EFFORT_TIMEOUT_SECONDS = 2.0


# 事件队列：run_id → asyncio.Queue
_event_queues: dict[str, asyncio.Queue] = {}
_run_starts: dict[str, float] = {}
_run_tasks: dict[str, asyncio.Task] = {}


def _summarize_usage(usage_by_agent: dict | None) -> tuple[int, int]:
    """Return (total_tokens, cost_cents) from per-agent usage."""
    total_tokens = 0
    cost_cents = 0
    for info in (usage_by_agent or {}).values():
        if not isinstance(info, dict):
            continue
        total_tokens += int(info.get("total_tokens") or 0)
        total_tokens += int(info.get("input_tokens") or 0)
        total_tokens += int(info.get("output_tokens") or 0)
        cost_cents += int(info.get("cost_cents") or 0)
    return total_tokens, cost_cents


async def _update_run_db(run_id: str, **fields) -> bool:
    """Best-effort DB persistence; memory store remains the local fallback."""
    try:
        from app.db.models import Run
        from app.db.session import get_session

        allowed = {
            "status",
            "current_agent",
            "draft_md",
            "final_md",
            "topic",
            "outline",
            "final_outline",
            "images",
            "review",
            "revise_count",
            "cost_cents",
            "total_tokens",
            "usage_by_agent",
            "error",
            "ended_at",
        }
        async with get_session() as session:
            run = await session.get(Run, uuid.UUID(run_id))
            if not run:
                return False
            for key, value in fields.items():
                if key in allowed:
                    setattr(run, key, value)
            run.updated_at = datetime.utcnow()
            await session.commit()
        return True
    except Exception:
        return False


async def _append_event_db(run_id: str, event_type: str, data: dict, ts_offset: float) -> bool:
    try:
        from app.db.models import RunEvent
        from app.db.session import get_session

        async with get_session() as session:
            session.add(
                RunEvent(
                    run_id=uuid.UUID(run_id),
                    ts_offset=ts_offset,
                    event_type=event_type,
                    data=data,
                )
            )
            await session.commit()
        return True
    except Exception:
        return False


def _get_event_queue(run_id: str) -> asyncio.Queue:
    if run_id not in _event_queues:
        _event_queues[run_id] = asyncio.Queue()
    return _event_queues[run_id]


async def emit_event(run_id: str, event_type: str, data: dict):
    """推送事件到 SSE 队列"""
    start = _run_starts.setdefault(run_id, time.monotonic())
    ts_offset = round(time.monotonic() - start, 3)

    memory_event = append_event(run_id, event_type, data)
    try:
        await asyncio.wait_for(
            _append_event_db(run_id, event_type, data, ts_offset),
            timeout=_DB_BEST_EFFORT_TIMEOUT_SECONDS,
        )
    except Exception:
        pass

    update_fields = None
    if event_type == "agent.start":
        update_fields = {"current_agent": data.get("agent")}
    elif event_type == "agent.done" and data.get("agent") == "topic":
        update_fields = {"topic": data.get("selected_topic") or {"title": data.get("topic")}}
    elif event_type == "agent.done" and data.get("usage"):
        usage = data.get("usage") or {}
        total_tokens = int(usage.get("total_tokens") or 0)
        if not total_tokens:
            total_tokens = int(usage.get("input_tokens") or 0) + int(usage.get("output_tokens") or 0)
        cost_cents = int(usage.get("cost_cents") or 0)
        if total_tokens or cost_cents:
            current = upsert_run(run_id)
            update_fields = {
                "total_tokens": int(current.get("total_tokens") or 0) + total_tokens,
                "cost_cents": int(current.get("cost_cents") or 0) + cost_cents,
            }
    elif event_type == "graph.done":
        update_fields = {"status": "done", "current_agent": None}
    elif event_type == "graph.error":
        error_text = str(data.get("error") or "")
        status = "aborted" if "aborted by user" in error_text.lower() else "failed"
        update_fields = {"status": status, "error": data.get("error"), "current_agent": None}
    if update_fields:
        upsert_run(run_id, **update_fields)
        try:
            await asyncio.wait_for(
                _update_run_db(run_id, **update_fields),
                timeout=_DB_BEST_EFFORT_TIMEOUT_SECONDS,
            )
        except Exception:
            pass

    queue = _get_event_queue(run_id)
    await queue.put({"event": event_type, "id": str(memory_event.get("id")), "data": data})


async def get_event_stream(run_id: str, after_id: int = 0):
    """SSE 事件流生成器"""
    queue = _get_event_queue(run_id)
    while True:
        try:
            event = await asyncio.wait_for(queue.get(), timeout=30.0)
            yield event
        except asyncio.TimeoutError:
            yield {"event": "heartbeat", "data": {}}


async def start_run(run_id: str, user_request: str, target_platform: str = "wechat",
                    style_id: str | None = None, mock: bool = False) -> dict:
    """启动一个生成任务"""
    initial_state: ContentState = {
        "run_id": run_id,
        "user_request": user_request,
        "user_preferences": {},
        "target_platform": target_platform,
        "style_id": style_id,
        "topic": None,
        "outline": None,
        "sub_queries": None,
        "snippets": [],
        "final_outline": None,
        "draft_md": None,
        "images": [],
        "review": None,
        "revise_count": 0,
        "cost_cents": 0,
        "usage_by_agent": {},
    }

    budget = BudgetGuard(
        run_id,
        warn_callback=lambda data: asyncio.ensure_future(
            emit_event(run_id, "budget.warning", data)
        ),
    )
    config = {
        "configurable": {
            "thread_id": run_id,
            "mock": mock,
            "run_id": run_id,
            "budget": budget,
        }
    }

    start_time = time.monotonic()
    _run_starts[run_id] = start_time

    try:
        graph = await acompile_graph()
        await emit_event(run_id, "graph.start", {"run_id": run_id})
        # 15 分钟硬超时
        result = await asyncio.wait_for(
            graph.ainvoke(initial_state, config=config),
            timeout=_RUN_TIMEOUT_SECONDS,
        )
        elapsed = time.monotonic() - start_time
        total_tokens, usage_cost_cents = _summarize_usage(result.get("usage_by_agent"))
        cost_cents = int(result.get("cost_cents") or usage_cost_cents or 0)

        await emit_event(run_id, "graph.done", {
            "run_id": run_id,
            "status": "done",
            "elapsed_seconds": round(elapsed, 1),
            "words": len(result.get("draft_md", "")),
            "images": len(result.get("images", [])),
        })
        upsert_run(
            run_id,
            status="done",
            draft_md=result.get("draft_md"),
            final_md=result.get("draft_md"),
            topic=result.get("topic"),
            outline=result.get("outline"),
            final_outline=result.get("final_outline"),
            images=result.get("images") or [],
            review=result.get("review"),
            revise_count=result.get("revise_count", 0),
            cost_cents=cost_cents,
            total_tokens=total_tokens,
            usage_by_agent=result.get("usage_by_agent", {}),
            ended_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
        await _update_run_db(
            run_id,
            status="done",
            current_agent=None,
            draft_md=result.get("draft_md"),
            final_md=result.get("draft_md"),
            topic=result.get("topic"),
            outline=result.get("outline"),
            final_outline=result.get("final_outline"),
            images=result.get("images") or [],
            review=result.get("review"),
            revise_count=result.get("revise_count", 0),
            cost_cents=cost_cents,
            total_tokens=total_tokens,
            usage_by_agent=result.get("usage_by_agent", {}),
            ended_at=datetime.utcnow(),
        )
        return result

    except Exception as e:
        elapsed = time.monotonic() - start_time
        error_text = str(e) or repr(e)
        await emit_event(run_id, "graph.error", {
            "run_id": run_id,
            "error": error_text,
            "elapsed_seconds": round(elapsed, 1),
        })
        upsert_run(run_id, status="failed", error=error_text)
        await _update_run_db(run_id, status="failed", current_agent=None, error=error_text, ended_at=datetime.utcnow())
        raise


async def start_run_background(run_id: str, user_request: str, target_platform: str = "wechat",
                               style_id: str | None = None, mock: bool = False):
    """在后台运行任务（FastAPI BackgroundTasks 调用）"""
    task = asyncio.current_task()
    if task:
        _run_tasks[run_id] = task
    try:
        await start_run(run_id, user_request, target_platform, style_id, mock)
    except asyncio.CancelledError:
        await emit_event(run_id, "graph.error", {"run_id": run_id, "error": "aborted by user"})
        upsert_run(run_id, status="aborted")
        await _update_run_db(run_id, status="aborted", current_agent=None, ended_at=datetime.utcnow())
    except Exception as e:
        print(f"[runner] run {run_id} failed: {e}")
    finally:
        _run_tasks.pop(run_id, None)


async def cancel_run(run_id: str) -> bool:
    """取消正在运行的任务"""
    task = _run_tasks.get(run_id)
    if task and not task.done():
        task.cancel()
        return True
    return False
