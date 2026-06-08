"""LangGraph 状态机 — 编排 8 个 agent 节点

照搬 PRD §4.10 的 ContentState 和 Graph 构建。
"""

from __future__ import annotations

import json
import sys
import uuid
from operator import add
from pathlib import Path
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_CHECKPOINTER_CTX = None
_CHECKPOINTER = None
_ASYNC_CHECKPOINTER_CTX = None
_ASYNC_CHECKPOINTER = None


def _merge_usage(a: dict, b: dict) -> dict:
    """合并 usage_by_agent — 同名 agent 累加 token 计数"""
    merged = dict(a)
    for key, val in b.items():
        if key in merged and isinstance(val, dict) and isinstance(merged[key], dict):
            merged[key] = {
                k: (merged[key].get(k, 0) or 0) + (val.get(k, 0) or 0)
                for k in set(list(merged[key].keys()) + list(val.keys()))
            }
        else:
            merged[key] = val
    return merged


class ContentState(TypedDict):
    # 输入
    run_id: str
    user_request: str
    user_preferences: dict  # {topics, styles, avoid_keywords}
    target_platform: str
    style_id: str | None

    # 中间产物
    topic: dict | None
    outline: list[dict] | None
    sub_queries: list[str] | None
    snippets: Annotated[list[dict], add]  # reducer：并发追加
    final_outline: dict | None
    draft_md: str | None
    images: list[dict]  # IllustratorAgent 填充

    # 审阅
    review: dict | None
    revise_count: int

    # 计量 — Annotated reducer 支持并发 fan-out 写入
    cost_cents: Annotated[int, add]
    usage_by_agent: Annotated[dict, _merge_usage]


def research_dispatcher(state: ContentState):
    """fan-out：N 个 sub_query → N 个 researcher_worker 并行"""
    from langgraph.types import Send

    sub_queries = state.get("sub_queries") or []
    return [
        Send("researcher_worker", {"query": q, "run_id": state["run_id"]})
        for q in sub_queries
    ]


def review_gate(state: ContentState) -> str:
    """条件边：pass/score>=7 → END / fail & count<2 → reviser / fail & count≥2 → needs_human"""
    review = state.get("review") or {}
    # pass=True 或 score>=7.0 都视为通过（避免不必要的修订循环）
    if review.get("pass") or (review.get("score", 0) >= 7.0):
        return "done"
    if state.get("revise_count", 0) >= 2:
        return "needs_human"
    return "revise"


def build_graph():
    """构建并编译 LangGraph 状态机"""
    from app.agents.topic import topic_agent
    from app.agents.planner import planner_agent
    from app.agents.researcher import researcher_worker
    from app.agents.editor import editor_agent
    from app.agents.writer import writer_agent
    from app.agents.illustrator import illustrator_agent
    from app.agents.reviewer import reviewer_agent
    from app.agents.reviser import reviser_agent
    from app.workers.runner import emit_event

    async def needs_human_node(state: ContentState, config=None):
        """终态：修订轮次耗尽，需要人工介入"""
        configurable = config.get("configurable", {}) if config else {}
        run_id = configurable.get("run_id") or state.get("run_id", "")
        await emit_event(run_id, "needs_human", {
            "revise_count": state.get("revise_count", 0),
            "review": state.get("review"),
        })
        return {"review": {**(state.get("review") or {}), "needs_human": True}}

    g = StateGraph(ContentState)

    g.add_node("topic", topic_agent)
    g.add_node("planner", planner_agent)
    g.add_node("researcher_worker", researcher_worker)
    g.add_node("editor", editor_agent)
    g.add_node("writer", writer_agent)
    g.add_node("illustrator", illustrator_agent)
    g.add_node("reviewer", reviewer_agent)
    g.add_node("reviser", reviser_agent)
    g.add_node("needs_human", needs_human_node)

    g.set_entry_point("topic")
    g.add_edge("topic", "planner")

    # fan-out：N 个 sub_query → N 个 researcher_worker 并行
    g.add_conditional_edges("planner", research_dispatcher, ["researcher_worker"])

    # fan-in：所有 worker 完成后聚合到 editor
    g.add_edge("researcher_worker", "editor")
    g.add_edge("editor", "writer")
    g.add_edge("writer", "illustrator")
    g.add_edge("illustrator", "reviewer")

    # 条件边：pass → END；fail & count<2 → reviser；fail & count≥2 → needs_human
    g.add_conditional_edges("reviewer", review_gate, {"done": END, "revise": "reviser", "needs_human": "needs_human"})
    g.add_edge("reviser", "reviewer")
    g.add_edge("needs_human", END)

    return g


def compile_graph():
    """同步编译图；异步运行请使用 acompile_graph 以启用 AsyncPostgresSaver。"""
    import os

    g = build_graph()

    if os.getenv("ACF_ENABLE_CHECKPOINT") != "1":
        return g.compile()

    raise RuntimeError("ACF_ENABLE_CHECKPOINT=1 requires acompile_graph()")


async def acompile_graph():
    """异步编译图，使用 AsyncPostgresSaver checkpoint。"""
    import os

    g = build_graph()

    if os.getenv("ACF_ENABLE_CHECKPOINT") != "1":
        return g.compile()

    pg_url = os.getenv("DATABASE_URL", "").replace("+psycopg", "")
    if not pg_url:
        raise RuntimeError("ACF_ENABLE_CHECKPOINT=1 but DATABASE_URL is empty")

    global _ASYNC_CHECKPOINTER_CTX, _ASYNC_CHECKPOINTER
    if _ASYNC_CHECKPOINTER is None:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        _ASYNC_CHECKPOINTER_CTX = AsyncPostgresSaver.from_conn_string(pg_url)
        _ASYNC_CHECKPOINTER = await _ASYNC_CHECKPOINTER_CTX.__aenter__()
        await _ASYNC_CHECKPOINTER.setup()

    return g.compile(checkpointer=_ASYNC_CHECKPOINTER)


# CLI 入口
if __name__ == "__main__":
    import asyncio

    async def _run_mock():
        state: ContentState = {
            "run_id": str(uuid.uuid4()),
            "user_request": "随便写一篇关于 AI 的文章",
            "user_preferences": {},
            "target_platform": "wechat",
            "style_id": None,
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

        graph = await acompile_graph()
        config = {"configurable": {"thread_id": state["run_id"]}}
        result = await graph.ainvoke(state, config=config)
        print(json.dumps({"status": "done", "run_id": result["run_id"]}, indent=2))

    if "--mock" in sys.argv:
        asyncio.run(_run_mock())
