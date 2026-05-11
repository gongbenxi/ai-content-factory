"""PlannerAgent — 规划：拆成大纲 + N 个研究子问题"""

from __future__ import annotations

import json
from pathlib import Path

from app.llm.client import LLMClient
from app.workers.runner import emit_event

_PROMPT = (Path(__file__).resolve().parents[1] / "llm" / "prompts" / "planner.txt").read_text()


async def planner_agent(state: dict, config=None) -> dict:
    """LangGraph node: PlannerAgent"""
    configurable = config.get("configurable", {}) if config else {}
    mock = configurable.get("mock", False)
    run_id = configurable.get("run_id") or state.get("run_id", "")
    budget = configurable.get("budget")

    await emit_event(run_id, "agent.start", {"agent": "planner"})

    llm = LLMClient(run_id=run_id, budget=budget)
    topic = state.get("topic", {})
    messages = [
        {"role": "system", "content": _PROMPT},
        {"role": "user", "content": f"选题: {json.dumps(topic, ensure_ascii=False)}"},
    ]

    result, usage = await llm.chat_json("planner", messages, mock=mock)

    outline = result.get("outline", [])
    sub_queries = result.get("sub_queries", [])

    await emit_event(run_id, "agent.done", {
        "agent": "planner",
        "sections": len(outline),
        "queries": len(sub_queries),
        "usage": usage,
    })

    return {
        "outline": outline,
        "sub_queries": sub_queries,
        "cost_cents": usage.get("cost_cents", 0),
        "usage_by_agent": {"planner": {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cost_cents": usage.get("cost_cents", 0),
        }},
    }
