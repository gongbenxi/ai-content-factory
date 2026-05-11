"""ReviewerAgent — 审稿：校验图文一致性 + 风格 + 合规"""

from __future__ import annotations

import json
from pathlib import Path

from app.llm.client import LLMClient
from app.tools.safety import content_safety_check
from app.workers.runner import emit_event

_PROMPT = (Path(__file__).resolve().parents[1] / "llm" / "prompts" / "reviewer.txt").read_text()


async def reviewer_agent(state: dict, config=None) -> dict:
    """LangGraph node: ReviewerAgent"""
    configurable = config.get("configurable", {}) if config else {}
    mock = configurable.get("mock", False)
    run_id = configurable.get("run_id") or state.get("run_id", "")
    budget = configurable.get("budget")

    await emit_event(run_id, "agent.start", {"agent": "reviewer"})

    draft_md = state.get("draft_md", "")
    images = state.get("images", [])
    target_platform = state.get("target_platform", "wechat")

    issues = []

    if draft_md and not mock:
        safety_result = content_safety_check(draft_md)
        await emit_event(run_id, "tool.call", {"agent": "reviewer", "tool": "content_safety_check", "safe": safety_result["safe"]})
        if not safety_result["safe"]:
            for hit in safety_result["issues"]:
                issues.append({
                    "type": "safety",
                    "detail": f"敏感词: {hit['keyword']}",
                    "severity": "critical",
                })

    llm = LLMClient(run_id=run_id, budget=budget)
    system_prompt = _PROMPT.format(target_platform=target_platform)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": (
            f"草稿:\n{draft_md[:3000]}\n\n"
            f"配图信息:\n{json.dumps(images, ensure_ascii=False)[:1000]}\n\n"
            f"已发现的安全问题:\n{json.dumps(issues, ensure_ascii=False)}"
        )},
    ]

    result, usage = await llm.chat_json("reviewer", messages, mock=mock)

    all_issues = issues + result.get("issues", [])

    review = {
        "pass": result.get("pass", True),
        "score": result.get("score", 8.0),
        "issues": all_issues,
        "summary": result.get("summary", ""),
    }

    await emit_event(run_id, "agent.done", {
        "agent": "reviewer",
        "pass": review["pass"],
        "score": review["score"],
        "usage": usage,
    })
    await emit_event(run_id, "review.done", {
        "pass": review["pass"],
        "score": review["score"],
        "issues_count": len(review["issues"]),
        "summary": review["summary"],
    })

    return {
        "review": review,
        "cost_cents": usage.get("cost_cents", 0),
        "usage_by_agent": {"reviewer": {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cost_cents": usage.get("cost_cents", 0),
        }},
    }
