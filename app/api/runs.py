"""Runs API — 生成任务 CRUD + SSE"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.workers.runner import start_run_background, get_event_stream, _event_queues, cancel_run
from app.services.memory_store import EVENTS, RUNS, upsert_run

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateRunRequest(BaseModel):
    user_request: str = "写一篇热门文章"
    style_id: str | None = None
    target_platform: str = "wechat"
    mock: bool = False
    config: dict = {}  # {research_parallel, max_revise_rounds, max_images, budget_limit_cents}


class ResumeRequest(BaseModel):
    state_patch: dict = {}


async def _try_db_write_run(run_id: str, req: CreateRunRequest) -> bool:
    try:
        from sqlalchemy import select
        from app.db.session import get_session
        from app.db.models import Run
        async with get_session() as session:
            run = Run(
                id=uuid.UUID(run_id),
                user_request=req.user_request,
                style_id=req.style_id,
                target_platform=req.target_platform,
                config={"mock": req.mock, **req.config},
                status="drafting",
            )
            session.add(run)
            await session.commit()
        return True
    except Exception as e:
        logger.debug(f"DB write skipped: {e}")
        return False


@router.post("")
async def create_run(req: CreateRunRequest, bg: BackgroundTasks):
    """创建并启动一次生成任务"""
    run_id = str(uuid.uuid4())

    db_ok = await _try_db_write_run(run_id, req)
    if not db_ok:
        upsert_run(
            run_id,
            user_request=req.user_request,
            status="drafting",
            style_id=req.style_id,
            target_platform=req.target_platform,
            mock=req.mock,
        )

    bg.add_task(start_run_background, run_id, req.user_request, req.target_platform, req.style_id, req.mock)
    return {"run_id": run_id, "status": "drafting"}


@router.get("")
async def list_runs(status: str | None = None, limit: int = Query(20, le=100)):
    """运行列表"""
    try:
        from sqlalchemy import select, desc
        from app.db.session import get_session
        from app.db.models import Run
        async with get_session() as session:
            stmt = select(Run).order_by(desc(Run.created_at)).limit(limit)
            if status:
                stmt = stmt.where(Run.status == status)
            result = await session.execute(stmt)
            rows = result.scalars().all()
        return {
            "runs": [
                {
                    "id": str(r.id),
                    "user_request": r.user_request,
                    "status": r.status,
                    "current_agent": r.current_agent,
                    "cost_cents": r.cost_cents,
                    "total_tokens": r.total_tokens,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ],
            "total": len(rows),
        }
    except Exception:
        runs = list(RUNS.values())[-limit:]
        if status:
            runs = [r for r in runs if r.get("status") == status]
        return {"runs": runs, "total": len(runs), "_source": "memory"}


@router.get("/{run_id}")
async def get_run(run_id: str):
    """单条详情"""
    try:
        from app.db.session import get_session
        from app.db.models import Run
        async with get_session() as session:
            run = await session.get(Run, uuid.UUID(run_id))
            if not run:
                raise ValueError("not found in db")
        data = {
            "run_id": str(run.id),
            "user_request": run.user_request,
            "status": run.status,
            "current_agent": run.current_agent,
            "topic": run.topic,
            "outline": run.outline,
            "final_outline": run.final_outline,
            "draft_md": run.draft_md,
            "final_md": run.final_md,
            "images": run.images,
            "review": run.review,
            "revise_count": run.revise_count,
            "cost_cents": run.cost_cents,
            "total_tokens": run.total_tokens,
            "usage_by_agent": run.usage_by_agent,
            "error": run.error,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "ended_at": run.ended_at.isoformat() if run.ended_at else None,
            "created_at": run.created_at.isoformat() if run.created_at else None,
        }
        if run_id in RUNS:
            memory = RUNS[run_id]
            for key, value in memory.items():
                if value is not None:
                    data[key] = value
            data["run_id"] = run_id
        return data
    except Exception:
        if run_id in RUNS:
            return {"run_id": run_id, **RUNS[run_id]}
        return {"run_id": run_id, "status": "unknown", "_source": "memory"}


@router.get("/{run_id}/stream")
async def run_stream(run_id: str):
    """SSE 实时事件流"""
    async def event_generator():
        async for event in get_event_stream(run_id):
            yield event

    return EventSourceResponse(event_generator())


@router.get("/{run_id}/events")
async def get_events(run_id: str, after_id: int = 0):
    """历史事件"""
    try:
        from sqlalchemy import select
        from app.db.session import get_session
        from app.db.models import RunEvent
        async with get_session() as session:
            stmt = (
                select(RunEvent)
                .where(RunEvent.run_id == uuid.UUID(run_id), RunEvent.id > after_id)
                .order_by(RunEvent.id)
                .limit(200)
            )
            result = await session.execute(stmt)
            rows = result.scalars().all()
        events = [
                {"id": r.id, "event": r.event_type, "data": r.data, "ts_offset": r.ts_offset}
                for r in rows
            ]
        if not events and EVENTS.get(run_id):
            events = [e for e in EVENTS.get(run_id, []) if e["id"] > after_id]
            return {"events": events, "run_id": run_id, "_source": "memory"}
        return {"events": events, "run_id": run_id}
    except Exception:
        rows = [e for e in EVENTS.get(run_id, []) if e["id"] > after_id]
        return {"events": rows, "run_id": run_id, "_source": "memory"}


@router.post("/{run_id}/interrupt")
async def interrupt_run(run_id: str):
    """人工介入"""
    try:
        from app.db.session import get_session
        from app.db.models import Run
        async with get_session() as session:
            run = await session.get(Run, uuid.UUID(run_id))
            if run:
                run.status = "paused"
                await session.commit()
    except Exception:
        if run_id in RUNS:
            RUNS[run_id]["status"] = "paused"
    return {"run_id": run_id, "status": "paused"}


@router.post("/{run_id}/resume")
async def resume_run(run_id: str, body: ResumeRequest | None = None):
    """修改 state 后继续"""
    patched_keys = list((body.state_patch or {}).keys()) if body else []
    try:
        from app.db.session import get_session
        from app.db.models import Run
        async with get_session() as session:
            run = await session.get(Run, uuid.UUID(run_id))
            if run:
                run.status = "drafting"
                if body and body.state_patch:
                    for key, val in body.state_patch.items():
                        if hasattr(run, key):
                            setattr(run, key, val)
                await session.commit()
    except Exception:
        if run_id in RUNS:
            RUNS[run_id]["status"] = "drafting"
            if body and body.state_patch:
                RUNS[run_id].update(body.state_patch)
    return {"run_id": run_id, "status": "resumed", "patched": patched_keys}


@router.post("/{run_id}/abort")
async def abort_run(run_id: str):
    """中止运行 — 真实取消 asyncio.Task"""
    cancelled = await cancel_run(run_id)
    # DB/memory 状态更新（即使 task 已结束也写入）
    try:
        from app.db.session import get_session
        from app.db.models import Run
        async with get_session() as session:
            run = await session.get(Run, uuid.UUID(run_id))
            if run:
                run.status = "aborted"
                run.ended_at = datetime.utcnow()
                await session.commit()
    except Exception:
        if run_id in RUNS:
            RUNS[run_id]["status"] = "aborted"
    if run_id in _event_queues:
        del _event_queues[run_id]
    return {"run_id": run_id, "status": "aborted", "task_cancelled": cancelled}


@router.put("/{run_id}/article")
async def update_article(run_id: str, body: dict):
    """编辑草稿"""
    try:
        from app.db.session import get_session
        from app.db.models import Run
        async with get_session() as session:
            run = await session.get(Run, uuid.UUID(run_id))
            if run:
                if "draft_md" in body:
                    run.draft_md = body["draft_md"]
                if "final_md" in body:
                    run.final_md = body["final_md"]
                await session.commit()
    except Exception:
        if run_id in RUNS:
            if "draft_md" in body:
                RUNS[run_id]["draft_md"] = body["draft_md"]
            if "final_md" in body:
                RUNS[run_id]["final_md"] = body["final_md"]
    return {"run_id": run_id, "updated": True}


@router.post("/{run_id}/complete")
async def complete_run(run_id: str):
    """标记完成"""
    try:
        from app.db.session import get_session
        from app.db.models import Run
        async with get_session() as session:
            run = await session.get(Run, uuid.UUID(run_id))
            if run:
                run.status = "done"
                run.ended_at = datetime.utcnow()
                if not run.final_md and run.draft_md:
                    run.final_md = run.draft_md
                await session.commit()
    except Exception:
        if run_id in RUNS:
            RUNS[run_id]["status"] = "done"
            if not RUNS[run_id].get("final_md"):
                RUNS[run_id]["final_md"] = RUNS[run_id].get("draft_md", "")
    return {"run_id": run_id, "status": "done"}


@router.get("/{run_id}/export")
async def export_run(run_id: str, format: str = "md"):
    """导出 markdown"""
    content = ""
    try:
        from app.db.session import get_session
        from app.db.models import Run
        async with get_session() as session:
            run = await session.get(Run, uuid.UUID(run_id))
            if run:
                content = run.final_md or run.draft_md or ""
    except Exception:
        if run_id in RUNS:
            content = RUNS[run_id].get("final_md") or RUNS[run_id].get("draft_md") or ""
    return PlainTextResponse(content, media_type="text/markdown")


@router.post("/{run_id}/retry")
async def retry_from_agent(run_id: str, from_agent: str = ""):
    """从指定 agent 重试"""
    try:
        from app.db.session import get_session
        from app.db.models import Run
        async with get_session() as session:
            run = await session.get(Run, uuid.UUID(run_id))
            if run:
                run.status = "drafting"
                run.current_agent = from_agent
                await session.commit()
    except Exception:
        pass
    return {"run_id": run_id, "from_agent": from_agent, "status": "retrying"}


class RegenerateImageRequest(BaseModel):
    index: int = 0  # 图片在 images 列表中的索引


@router.post("/{run_id}/regenerate-image")
async def regenerate_image(run_id: str, body: RegenerateImageRequest):
    """重新生成指定索引的配图"""
    from app.tools.image import enhance_prompt, generate_image

    # 获取当前 run 数据
    images = []
    style_id = "default"
    draft_md = ""
    try:
        from app.db.session import get_session
        from app.db.models import Run
        async with get_session() as session:
            run = await session.get(Run, uuid.UUID(run_id))
            if run:
                images = list(run.images or [])
                style_id = run.style_id or "default"
                draft_md = run.draft_md or ""
    except Exception:
        run_data = RUNS.get(run_id, {})
        images = list(run_data.get("images", []))
        style_id = run_data.get("style_id", "default")
        draft_md = run_data.get("draft_md", "")

    idx = body.index
    if idx < 0 or idx >= len(images):
        return {"error": f"index {idx} out of range (0-{len(images) - 1})"}

    old_img = images[idx]
    placeholder = {
        "para_id": idx,
        "description": old_img.get("description", "重新生成的图片"),
        "ratio": old_img.get("ratio", "16:9"),
        "type": old_img.get("type", "illustration"),
        "context_before": draft_md[:400],
        "context_after": "",
    }

    enhanced = await enhance_prompt(placeholder, style_id=style_id, mock=False)
    result = await generate_image(enhanced, placeholder["type"], placeholder["ratio"])

    new_img = {
        "para_id": idx,
        "url": result.get("url", ""),
        "local_path": result.get("local_path", ""),
        "description": placeholder["description"],
        "type": placeholder["type"],
        "ratio": placeholder["ratio"],
        "model": result.get("model", ""),
    }
    images[idx] = new_img

    # 持久化
    try:
        from app.db.session import get_session
        from app.db.models import Run
        async with get_session() as session:
            run = await session.get(Run, uuid.UUID(run_id))
            if run:
                run.images = images
                await session.commit()
    except Exception:
        if run_id in RUNS:
            RUNS[run_id]["images"] = images

    return {"run_id": run_id, "index": idx, "image": new_img}
