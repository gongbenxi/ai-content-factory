"""
后台运行管理 — 桥接 Agent Graph 与数据库 + SSE
================================================================

职责：
    1. start_run() — 创建 DB 记录，在后台启动 graph
    2. 实时将 ContentState.emit() 事件写入 run_events 表
    3. 实时更新 runs 表状态
    4. 异常处理：失败写 error 字段

用法:
    from app.services.runner import start_run, get_active_runs
    run_id = await start_run(user_request="...", style_id="caoz")
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from app.db import create_run, update_run, append_event, get_run
from app.agents.graph import ContentState, run_graph, AgentLLM


# ============================================================
# 运行管理
# ============================================================

# 内存中跟踪活跃的 run 任务 {run_id: asyncio.Task}
_active_runs: dict[str, asyncio.Task] = {}


# Agent → run status 映射
_AGENT_STATUS_MAP = {
    "topic": "drafting",
    "planner": "drafting",
    "research": "drafting",
    "editor": "drafting",
    "writer": "drafting",
    "illustrator": "drafting",
    "reviewer": "reviewing",
    "reviser": "reviewing",
}


async def start_run(
    user_request: str = "",
    style_id: str = "caoz",
    target_platform: str = "wechat",
    use_mock: bool = False,
    force_review_fail: bool = False,
) -> str:
    """启动一次内容生成 run，返回 run_id。

    Args:
        user_request: 用户指令
        style_id: 风格指纹 ID
        target_platform: 目标平台
        use_mock: 是否使用 Mock 模式
        force_review_fail: 是否强制首轮审阅不通过（测试用）

    Returns:
        run_id: 运行记录 ID
    """
    # 创建 DB 记录
    db_run = create_run(
        user_request=user_request,
        style_id=style_id,
        target_platform=target_platform,
    )
    run_id = db_run["id"]

    # 创建 LLM 客户端
    real_client = None if use_mock else _try_create_llm()
    llm = AgentLLM(real_client=real_client, force_review_fail_first=force_review_fail)

    # 构造初始状态
    state = ContentState(
        user_request=user_request,
        style_id=style_id,
        target_platform=target_platform,
    )

    # 用实际 run_id 覆盖自动生成的（保持一致）
    state.run_id = run_id

    # 拦截 emit → 同时写 DB
    original_emit = state.emit

    def db_emit(event_type: str, **data) -> None:
        # 调用原始 emit（打印到控制台 + 追加到 state.events）
        original_emit(event_type, **data)

        # 写入 DB 事件流
        ts_offset = round(time.time() - state.started_at, 2)
        append_event(run_id, ts_offset, event_type, data)

        # 实时更新 run 状态
        _sync_run_status(run_id, event_type, data, state)

    state.emit = db_emit  # type: ignore

    # 后台启动 graph
    task = asyncio.create_task(_run_with_error_handling(run_id, state, llm))
    _active_runs[run_id] = task

    return run_id


def get_active_runs() -> list[str]:
    """获取当前正在运行的 run_id 列表。"""
    # 清理已完成的任务
    done = [rid for rid, t in _active_runs.items() if t.done()]
    for rid in done:
        del _active_runs[rid]
    return list(_active_runs.keys())


def is_run_active(run_id: str) -> bool:
    """检查指定 run 是否正在运行。"""
    task = _active_runs.get(run_id)
    if task is None:
        return False
    if task.done():
        del _active_runs[run_id]
        return False
    return True


async def abort_run(run_id: str) -> bool:
    """中止指定 run。"""
    task = _active_runs.get(run_id)
    if task is None or task.done():
        return False
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    update_run(run_id, status="needs_human", error="用户中止", ended_at=_now_iso())
    del _active_runs[run_id]
    return True


# ============================================================
# 内部函数
# ============================================================

def _try_create_llm():
    """尝试创建真 LLM 客户端，失败返回 None。"""
    try:
        from app.llm import create_llm
        return create_llm()
    except Exception:
        return None


async def _run_with_error_handling(
    run_id: str, state: ContentState, llm: AgentLLM
) -> None:
    """带异常处理的 graph 执行。"""
    try:
        final_state = await run_graph(state, llm)

        # 写入最终状态
        final_status = "done" if (final_state.review or {}).get("pass") else "needs_human"
        topic_json = json.dumps(final_state.topic, ensure_ascii=False) if final_state.topic else None
        images_json = json.dumps(final_state.images, ensure_ascii=False) if final_state.images else "[]"
        review_json = json.dumps(final_state.review, ensure_ascii=False) if final_state.review else None

        update_run(
            run_id,
            status=final_status,
            topic=json.loads(topic_json) if topic_json else None,
            final_md=final_state.draft_md,
            images=json.loads(images_json),
            review=json.loads(review_json) if review_json else None,
            cost_cents=final_state.cost_cents,
            ended_at=_now_iso(),
        )
    except asyncio.CancelledError:
        # 已被 abort_run 处理
        raise
    except Exception as e:
        update_run(
            run_id,
            status="needs_human",
            error=str(e),
            ended_at=_now_iso(),
        )
    finally:
        _active_runs.pop(run_id, None)


def _sync_run_status(
    run_id: str, event_type: str, data: dict, state: ContentState
) -> None:
    """根据事件实时更新 run 状态。"""
    parts = event_type.split(".")

    if parts[0] == "agent" and parts[1] == "start":
        agent = data.get("agent", "")
        status = _AGENT_STATUS_MAP.get(agent, "drafting")
        update_run(run_id, status=status, current_agent=agent)

    elif event_type == "graph.done":
        # 最终状态由 _run_with_error_handling 统一处理
        pass

    elif event_type == "review.done":
        if not data.get("passed", True):
            update_run(run_id, status="reviewing")


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
