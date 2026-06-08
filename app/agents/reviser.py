"""ReviserAgent — 修订：按 reviewer 反馈改稿"""

from __future__ import annotations

import json
from pathlib import Path

from app.llm.client import LLMClient
from app.workers.runner import emit_event

_PROMPT = (Path(__file__).resolve().parents[1] / "llm" / "prompts" / "reviser.txt").read_text()


async def reviser_agent(state: dict, config=None) -> dict:
    """LangGraph node: ReviserAgent"""
    configurable = config.get("configurable", {}) if config else {}
    mock = configurable.get("mock", False)
    run_id = configurable.get("run_id") or state.get("run_id", "")
    budget = configurable.get("budget")

    revise_count = state.get("revise_count", 0)

    await emit_event(run_id, "agent.start", {"agent": "reviser", "round": revise_count + 1})

    llm = LLMClient(run_id=run_id, budget=budget)
    draft_md = state.get("draft_md", "")
    review = state.get("review", {})

    messages = [
        {"role": "system", "content": _PROMPT},
        {"role": "user", "content": (
            f"当前草稿:\n{draft_md}\n\n"
            f"审稿意见:\n{json.dumps(review, ensure_ascii=False)}"
        )},
    ]

    content, usage = await llm.chat("reviser", messages, mock=mock, max_tokens=8192)

    # 去掉 LLM 可能包裹的 markdown 代码块标记
    stripped = content.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    await emit_event(run_id, "agent.done", {
        "agent": "reviser",
        "round": revise_count + 1,
        "usage": usage,
    })

    return {
        "draft_md": content,
        "revise_count": revise_count + 1,
        "cost_cents": usage.get("cost_cents", 0),
        "usage_by_agent": {"reviser": {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cost_cents": usage.get("cost_cents", 0),
        }},
    }
