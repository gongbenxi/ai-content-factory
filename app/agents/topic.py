"""TopicAgent — 选题：从热榜+用户偏好挑出今天写什么"""

from __future__ import annotations

from pathlib import Path
import re

from app.llm.client import LLMClient
from app.workers.runner import emit_event

_PROMPT = (Path(__file__).resolve().parents[1] / "llm" / "prompts" / "topic.txt").read_text()


def _normalize_requested_title(user_request: str) -> str:
    title = re.sub(r"\s+", " ", user_request or "").strip()
    title = re.sub(r"(模仿|参考)\s*[^。；;，,]*风格[^。；;，,。]*[。；;，,]?", "", title).strip()
    title = re.sub(r"(公众号文|小红书文案|知乎文章|抖音文案|文章)\s*[。；;，,]?$", "", title).strip()
    return title.strip(" ：:，,。；;") or "今日热点"


async def topic_agent(state: dict, config=None) -> dict:
    """LangGraph node: TopicAgent"""
    configurable = config.get("configurable", {}) if config else {}
    mock = configurable.get("mock", False)
    run_id = configurable.get("run_id") or state.get("run_id", "")
    budget = configurable.get("budget")

    await emit_event(run_id, "agent.start", {"agent": "topic"})

    llm = LLMClient(run_id=run_id, budget=budget)
    requested_title = _normalize_requested_title(state.get("user_request", "写一篇热门文章"))
    messages = [
        {"role": "system", "content": _PROMPT},
        {"role": "user", "content": (
            f"用户请求: {state.get('user_request', '写一篇热门文章')}\n"
            f"必须保持的主题标题: {requested_title}\n"
            f"用户偏好: {state.get('user_preferences', {})}"
        )},
    ]

    result, usage = await llm.chat_json("topic", messages, mock=mock)

    candidates = result.get("candidates", [])
    topic = candidates[0] if candidates else {"title": requested_title, "angle": "综合分析"}
    topic["title"] = requested_title
    topic["source_user_request"] = state.get("user_request", "")
    topic["target_platform"] = state.get("target_platform") or topic.get("target_platform", "wechat")

    await emit_event(run_id, "agent.done", {
        "agent": "topic",
        "topic": topic.get("title", ""),
        "selected_topic": topic,
        "usage": usage,
    })

    return {
        "topic": topic,
        "target_platform": topic.get("target_platform", state.get("target_platform", "wechat")),
        "cost_cents": usage.get("cost_cents", 0),
        "usage_by_agent": {"topic": {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cost_cents": usage.get("cost_cents", 0),
        }},
    }
