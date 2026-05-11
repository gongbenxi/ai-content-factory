"""EditorAgent — 编辑：合并素材 + 选定风格 + 出最终大纲"""

from __future__ import annotations

import json
from pathlib import Path

from app.llm.client import LLMClient
from app.workers.runner import emit_event

_PROMPT = (Path(__file__).resolve().parents[1] / "llm" / "prompts" / "editor.txt").read_text()


async def editor_agent(state: dict, config=None) -> dict:
    """LangGraph node: EditorAgent"""
    configurable = config.get("configurable", {}) if config else {}
    mock = configurable.get("mock", False)
    run_id = configurable.get("run_id") or state.get("run_id", "")
    budget = configurable.get("budget")

    await emit_event(run_id, "agent.start", {"agent": "editor"})

    llm = LLMClient(run_id=run_id, budget=budget)
    outline = state.get("outline", [])
    snippets = state.get("snippets", [])
    style_id = state.get("style_id", "default")

    messages = [
        {"role": "system", "content": _PROMPT},
        {"role": "user", "content": (
            f"原始大纲:\n{json.dumps(outline, ensure_ascii=False)}\n\n"
            f"研究素材 ({len(snippets)} 条):\n{json.dumps(snippets[:10], ensure_ascii=False)}\n\n"
            f"目标风格: {style_id}"
        )},
    ]

    result, usage = await llm.chat_json("editor", messages, mock=mock)

    await emit_event(run_id, "agent.done", {"agent": "editor", "usage": usage})

    return {
        "final_outline": result.get("final_outline", {}),
        "cost_cents": usage.get("cost_cents", 0),
        "usage_by_agent": {"editor": {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cost_cents": usage.get("cost_cents", 0),
        }},
    }
