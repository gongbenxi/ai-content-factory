"""
路由 — /api/runs/*（对应 PRD §6a）
================================================================
"""

from __future__ import annotations

import json
import asyncio

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

from app.models import (
    CreateRunRequest, RunResponse, RunListResponse, RunEventResponse,
)
from app.db import get_run, list_runs, get_events, update_run
from app.services.runner import start_run, is_run_active, abort_run

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.post("", response_model=RunResponse)
async def api_create_run(req: CreateRunRequest):
    """创建并启动生成（对应 PRD M1/M2）。"""
    run_id = await start_run(
        user_request=req.user_request,
        style_id=req.style_id,
        target_platform=req.target_platform,
        use_mock=False,
    )
    run = get_run(run_id)
    return _to_response(run)


@router.get("", response_model=RunListResponse)
async def api_list_runs(
    status: str | None = Query(None, description="按状态筛选"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """运行列表（分页+筛选）。"""
    items = list_runs(status=status, limit=limit, offset=offset)
    return RunListResponse(
        items=[_to_response(r) for r in items],
        total=len(items),
    )


@router.get("/{run_id}", response_model=RunResponse)
async def api_get_run(run_id: str):
    """单条运行详情。"""
    run = get_run(run_id)
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")
    return _to_response(run)


@router.get("/{run_id}/events")
async def api_run_events_sse(run_id: str):
    """SSE 实时事件流（对应 PRD M2）。"""
    run = get_run(run_id)
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")

    async def event_generator():
        last_id = 0
        # 先推送历史事件
        for evt in get_events(run_id):
            last_id = evt["id"]
            yield {
                "event": evt["event_type"],
                "data": evt["data"],
                "id": str(evt["id"]),
            }

        # 如果 run 还在跑，持续轮询新事件
        while is_run_active(run_id):
            await asyncio.sleep(0.3)
            new_events = get_events(run_id, after_id=last_id)
            for evt in new_events:
                last_id = evt["id"]
                yield {
                    "event": evt["event_type"],
                    "data": evt["data"],
                    "id": str(evt["id"]),
                }

        # run 结束，推送剩余事件
        for evt in get_events(run_id, after_id=last_id):
            yield {
                "event": evt["event_type"],
                "data": evt["data"],
                "id": str(evt["id"]),
            }

    return EventSourceResponse(event_generator())


@router.get("/{run_id}/events/history")
async def api_run_events_history(
    run_id: str,
    after_id: int = Query(0, description="增量拉取，返回 id > after_id 的事件"),
):
    """历史事件（非 SSE，用于回放）。"""
    run = get_run(run_id)
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")
    events = get_events(run_id, after_id=after_id)
    return [
        RunEventResponse(
            id=e["id"],
            run_id=e["run_id"],
            ts_offset=e["ts_offset"],
            event_type=e["event_type"],
            data=json.loads(e["data"]) if isinstance(e["data"], str) else e["data"],
            created_at=e["created_at"],
        )
        for e in events
    ]


@router.post("/{run_id}/abort")
async def api_abort_run(run_id: str):
    """中止运行。"""
    run = get_run(run_id)
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")
    success = await abort_run(run_id)
    if not success:
        raise HTTPException(400, f"Run {run_id} is not currently active")
    return {"status": "aborted", "run_id": run_id}


@router.put("/{run_id}/article")
async def api_edit_article(run_id: str, body: dict):
    """编辑草稿（对应 PRD M3）。"""
    run = get_run(run_id)
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")
    draft_md = body.get("draft_md")
    if not draft_md:
        raise HTTPException(400, "draft_md is required")
    update_run(run_id, draft_md=draft_md)
    return {"status": "updated", "run_id": run_id}


@router.post("/{run_id}/complete")
async def api_complete_run(run_id: str):
    """标记完成（对应 PRD M4）。"""
    run = get_run(run_id)
    if not run:
        raise HTTPException(404, f"Run {run_id} not found")
    update_run(run_id, status="done", final_md=run.get("draft_md", ""))
    return {"status": "done", "run_id": run_id}


def _to_response(run: dict) -> RunResponse:
    """DB row dict → RunResponse，处理 JSON 字段反序列化。"""
    return RunResponse(
        id=run["id"],
        user_request=run.get("user_request", ""),
        style_id=run.get("style_id", ""),
        target_platform=run.get("target_platform", "wechat"),
        topic=json.loads(run["topic"]) if run.get("topic") else None,
        status=run.get("status", "drafting"),
        current_agent=run.get("current_agent"),
        draft_md=run.get("draft_md"),
        final_md=run.get("final_md"),
        images=json.loads(run["images"]) if run.get("images") else [],
        review=json.loads(run["review"]) if run.get("review") else None,
        cost_cents=run.get("cost_cents", 0),
        error=run.get("error"),
        started_at=run.get("started_at", ""),
        ended_at=run.get("ended_at"),
        updated_at=run.get("updated_at", ""),
    )
