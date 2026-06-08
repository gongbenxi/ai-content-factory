"""WriterAgent — 撰写：基于 style_fingerprint 写正文

流式输出，前端实时展示。
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.llm.client import LLMClient
from app.workers.runner import emit_event

_PROMPT = (Path(__file__).resolve().parents[1] / "llm" / "prompts" / "writer.txt").read_text()
_STREAM_FLUSH_CHARS = 120
_STREAM_FLUSH_SECONDS = 0.5


async def _load_style_fingerprint(style_id: str | None) -> dict:
    """加载风格指纹，优先 DB，fallback memory_store"""
    if not style_id:
        return {}
    try:
        from app.db.session import get_session
        from app.db.models import Style
        async with get_session() as session:
            style = await session.get(Style, style_id)
            if style and style.fingerprint:
                return style.fingerprint
    except Exception:
        pass
    try:
        from app.services.memory_store import STYLES
        if style_id in STYLES:
            return STYLES[style_id].get("fingerprint", {})
    except Exception:
        pass
    return {}


async def writer_agent(state: dict, config=None) -> dict:
    """LangGraph node: WriterAgent"""
    configurable = config.get("configurable", {}) if config else {}
    mock = configurable.get("mock", False)
    run_id = configurable.get("run_id") or state.get("run_id", "")
    budget = configurable.get("budget")

    await emit_event(run_id, "agent.start", {"agent": "writer"})

    llm = LLMClient(run_id=run_id, budget=budget)
    final_outline = state.get("final_outline", {})
    snippets = state.get("snippets", [])
    target_platform = state.get("target_platform", "wechat")

    # 加载真实风格指纹
    style_id = state.get("style_id")
    fp = await _load_style_fingerprint(style_id)
    persona_name = style_id or "通用"
    syntax_patterns = fp.get("syntax_patterns", "短句为主，段落分明")
    top_words = ", ".join(fp.get("top_words", [])) or "AI, 大模型, 技术, 行业"
    rhetorical_features = fp.get("rhetorical_features", "善用比喻和对比")
    rep_sentences = fp.get("representative_sentences", [])
    examples = "\n".join(f"{i+1}. {s}" for i, s in enumerate(rep_sentences[:5])) or "1. 六百万美元，把硅谷震了\n2. 技术改变世界"

    system_prompt = _PROMPT.format(
        persona_name=persona_name,
        syntax_patterns=syntax_patterns,
        top_words=top_words,
        rhetorical_features=rhetorical_features,
        examples=examples,
        target_platform=target_platform,
        outline=json.dumps(final_outline, ensure_ascii=False),
        snippets=json.dumps(snippets[:10], ensure_ascii=False),
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "开始写作。"},
    ]

    # 流式输出
    chunks = []
    usage = {"input_tokens": 0, "output_tokens": 0, "cost_cents": 0}

    if mock:
        content, usage = await llm.chat("writer", messages, mock=True)
        chunks.append(content)
        await emit_event(run_id, "writer.token", {"delta": content})
    else:
        try:
            buffer = []
            last_flush = asyncio.get_running_loop().time()
            async for chunk in llm.stream("writer", messages, max_tokens=8192):
                chunks.append(chunk)
                buffer.append(chunk)
                now = asyncio.get_running_loop().time()
                buffered = "".join(buffer)
                if len(buffered) >= _STREAM_FLUSH_CHARS or (now - last_flush) >= _STREAM_FLUSH_SECONDS:
                    await emit_event(run_id, "writer.token", {"agent": "writer", "delta": buffered})
                    buffer.clear()
                    last_flush = now
            if buffer:
                await emit_event(run_id, "writer.token", {"agent": "writer", "delta": "".join(buffer)})
            if not chunks:
                raise RuntimeError("empty stream response")
        except Exception as exc:
            # fallback to non-streaming
            await emit_event(run_id, "agent.warning", {"agent": "writer", "message": f"stream fallback: {str(exc)[:160]}"})
            content, usage = await llm.chat("writer", messages, mock=False, max_tokens=8192)
            chunks.append(content)
            await emit_event(run_id, "writer.token", {"agent": "writer", "delta": content})

    content = "".join(chunks)

    # 粗略 token 统计（streaming 模式下不精确）
    if not usage.get("output_tokens"):
        usage = {
            "input_tokens": len(system_prompt) // 2,
            "output_tokens": len(content) // 2,
            "cost_cents": 0,
        }

    await emit_event(run_id, "agent.done", {
        "agent": "writer",
        "chars": len(content),
        "usage": usage,
    })

    return {
        "draft_md": content,
        "cost_cents": usage.get("cost_cents", 0),
        "usage_by_agent": {"writer": {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cost_cents": usage.get("cost_cents", 0),
        }},
    }
