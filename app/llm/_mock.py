"""Mock 响应 — 本地联调用，尽量跟随当前请求上下文。"""

from __future__ import annotations

import json
import re
from typing import Any

MOCK_RESPONSES = {
    "topic": json.dumps({
        "candidates": [
            {
                "title": "DeepSeek-V3 发布：国产大模型的新拐点",
                "angle": "技术突破 + 商业影响双线分析",
                "target_platform": "wechat",
                "hook": "六百万美元，把硅谷震了",
                "estimated_quality": 0.85,
            }
        ]
    }),
    "planner": json.dumps({
        "outline": [
            {"section": "DeepSeek-V3 性能数据", "intent": "建立技术事实"},
            {"section": "对比 GPT-4o 和 Claude Sonnet", "intent": "横向参照"},
            {"section": "训练成本分析", "intent": "揭示性价比优势"},
            {"section": "对行业的冲击", "intent": "讨论影响"},
        ],
        "sub_queries": [
            "DeepSeek-V3 在 MMLU/HumanEval 等基准的具体得分",
            "DeepSeek-V3 的训练成本和技术架构",
            "国产大模型竞争格局 2025",
            "AI 行业对 DeepSeek-V3 的反应",
        ],
    }),
    "researcher": json.dumps([
        {
            "source": "https://example.com/deepseek-v3",
            "title": "DeepSeek-V3 正式发布",
            "excerpt": "DeepSeek-V3 在 MMLU 上获得 87.5 分，超过 GPT-4o 的 86.0 分。训练成本仅为 557.6 万美元。",
            "credibility": 0.9,
            "angle": "数据",
        }
    ]),
    "editor": json.dumps({
        "final_outline": {
            "sections": [
                {"section": "DeepSeek-V3 性能数据", "intent": "建立技术事实", "cite_snippet_ids": [0], "target_words": 400},
                {"section": "对比 GPT-4o", "intent": "横向参照", "cite_snippet_ids": [0], "target_words": 300},
                {"section": "训练成本分析", "intent": "性价比优势", "cite_snippet_ids": [0], "target_words": 400},
                {"section": "行业冲击", "intent": "影响讨论", "cite_snippet_ids": [0], "target_words": 400},
            ]
        },
        "style_adjustments": "保留短句节奏；段落首句作为强观点钩子",
    }),
    "writer": """# 六百万美元，把硅谷震了

[IMG: 杭州深夜的办公楼，一扇窗亮着灯，工程师围着白板讨论模型架构，扁平插画风，冷蓝色调 | 16:9 | cover]

DeepSeek-V3 在 MMLU 上得了 87.5 分，碾压 GPT-4o 的 86.0。更狠的是训练成本——只花了 557.6 万美元。

[IMG: DeepSeek-V3 与 GPT-4o、Claude 3.5 在 MMLU/HumanEval 三项基准得分对比柱状图，蓝橙绿三色 | 16:9 | chart]

## 为什么这次震得不一样？

过去国产大模型追的是"我也能做到"。但 DeepSeek-V3 这次不只是追平，是在成本上打了个对折再对折。

557.6 万美元，相当于 OpenAI 一个月的电费。

## 训练成本到底怎么降的？

核心技术是 MoE（Mixture of Experts）架构的深度优化。671B 参数，但每个 token 只激活 37B。

[IMG: MoE 架构示意图，展示专家路由机制，多个子网络通过门控网络选择激活 | 16:9 | illustration]

## 对行业意味着什么？

这意味着大模型的门槛被彻底拉低了。以前大家觉得"没钱别玩 AI"，现在证明用十分之一的钱也能做到同样的事。

> "六百万美元，相当于 OpenAI 一个月电费。"

[IMG: 大字金句卡，引用文字"六百万美元，相当于 OpenAI 一个月电费"，深色背景白字 | 1:1 | card]
""",
    "reviewer": json.dumps({
        "pass": True,
        "score": 8.4,
        "issues": [],
        "summary": "图文一致，风格匹配，平台规范通过。",
    }),
    "reviser": "（mock 模式：Reviser 无需修订）",
    "illustrator": json.dumps({"status": "mock", "images": []}),
    "_default": "Mock response — no LLM configured.",
}


def build_mock_response(agent: str, messages: list[dict] | None = None) -> str:
    """Return a deterministic but context-aware mock response for an agent."""
    messages = messages or []
    user_text = "\n".join(str(m.get("content", "")) for m in messages if m.get("role") == "user")
    system_text = "\n".join(str(m.get("content", "")) for m in messages if m.get("role") == "system")

    if agent == "topic":
        return json.dumps(_mock_topic(user_text), ensure_ascii=False)
    if agent == "planner":
        return json.dumps(_mock_planner(user_text), ensure_ascii=False)
    if agent == "researcher":
        return json.dumps(_mock_researcher(user_text), ensure_ascii=False)
    if agent == "editor":
        return json.dumps(_mock_editor(user_text), ensure_ascii=False)
    if agent == "writer":
        return _mock_writer(system_text)
    if agent == "reviewer":
        return json.dumps({
            "pass": True,
            "score": 8.2,
            "issues": [],
            "summary": "mock 审阅通过：草稿主题一致，结构完整，可进入编辑器检查。",
        }, ensure_ascii=False)
    return MOCK_RESPONSES.get(agent, MOCK_RESPONSES["_default"])


def mock_usage(content: str) -> dict:
    output_tokens = max(1, len(content) // 2)
    return {
        "input_tokens": 0,
        "output_tokens": output_tokens,
        "total_tokens": output_tokens,
        "cost_cents": 0,
    }


def _extract_after(label: str, text: str) -> str:
    match = re.search(rf"{re.escape(label)}\s*[:：]\s*(.+)", text)
    return match.group(1).strip() if match else ""


def _short_title(text: str) -> str:
    title = text.strip().splitlines()[0] if text.strip() else "今日热点"
    title = re.sub(r"^(请)?(帮我)?(写|生成|撰写)(一篇|一个)?", "", title).strip(" ：:，,。")
    return title[:48] or "今日热点"


def _loads_embedded_json(text: str, label: str) -> Any:
    start = text.find(label)
    if start >= 0:
        text = text[start + len(label):]
    candidates = [(idx, opener, closer) for opener, closer in [("{", "}"), ("[", "]")] if (idx := text.find(opener)) >= 0]
    if not candidates:
        return None
    idx, opener, closer = min(candidates, key=lambda item: item[0])
    depth = 0
    for pos in range(idx, len(text)):
        ch = text[pos]
        if ch == opener:
            depth += 1
        elif ch == closer:
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[idx:pos + 1])
                except Exception:
                    return None
    return None


def _mock_topic(user_text: str) -> dict:
    request = _extract_after("用户请求", user_text) or user_text or "今日热点"
    title = _short_title(request)
    return {
        "candidates": [
            {
                "title": title,
                "angle": "基于用户指令的背景梳理、关键信息与影响分析",
                "target_platform": "wechat",
                "hook": f"{title}，真正值得看的不是标题，而是后续信号",
                "estimated_quality": 0.82,
            }
        ]
    }


def _mock_planner(user_text: str) -> dict:
    topic = _loads_embedded_json(user_text, "选题") or {}
    title = topic.get("title") or _short_title(user_text)
    return {
        "outline": [
            {"section": f"{title}：事件背景", "intent": "交代发生了什么和为什么值得关注"},
            {"section": "关键信息与各方表态", "intent": "梳理已经公开的核心信息"},
            {"section": "可能影响与后续观察", "intent": "分析这件事接下来会怎样发酵"},
            {"section": "写作结论", "intent": "给出适合公众号读者的判断"},
        ],
        "sub_queries": [
            f"{title} 最新官方信息",
            f"{title} 背景和关键细节",
            f"{title} 中方表态和外部反应",
            f"{title} 后续影响分析",
        ],
    }


def _mock_researcher(user_text: str) -> list[dict]:
    query = _extract_after("子问题", user_text) or _short_title(user_text)
    return [
        {
            "source": "mock://local-research",
            "title": f"{query} - 本地联调素材",
            "excerpt": f"围绕“{query}”，mock 研究素材提供背景、公开表态、时间线和后续观察点，供后续大纲与正文引用。",
            "credibility": 0.6,
            "angle": "背景",
        }
    ]


def _mock_editor(user_text: str) -> dict:
    outline = _loads_embedded_json(user_text, "原始大纲") or []
    if not isinstance(outline, list) or not outline:
        outline = _mock_planner(user_text)["outline"]
    title = outline[0].get("section", "今日热点").split("：")[0]
    sections = []
    for index, item in enumerate(outline[:4]):
        sections.append({
            "section": item.get("section", f"{title} 要点 {index + 1}"),
            "intent": item.get("intent", "展开关键事实和判断"),
            "cite_snippet_ids": [min(index, 3)],
            "target_words": 280,
        })
    return {
        "final_outline": {
            "title": title,
            "sections": sections,
        },
        "style_adjustments": "保持短段落、强观点句和清晰小标题。",
    }


def _mock_writer(system_text: str) -> str:
    outline = _loads_embedded_json(system_text, "文章：") or {}
    snippets = _loads_embedded_json(system_text, "必须引用") or []
    sections = outline.get("sections") if isinstance(outline, dict) else []
    title = outline.get("title") if isinstance(outline, dict) else None
    if not title and sections:
        title = sections[0].get("section", "今日热点").split("：")[0]
    title = title or "今日热点"

    facts = []
    for item in snippets[:4] if isinstance(snippets, list) else []:
        if isinstance(item, dict):
            facts.append(item.get("excerpt") or item.get("content") or item.get("title") or "")
    fact_text = facts[0] if facts else f"围绕“{title}”的公开信息仍在更新，当前更适合先梳理背景和后续观察点。"

    body = [
        f"# {title}",
        "",
        f"[IMG: {title}相关的新闻现场与信息流画面，突出事件背景和公众关注 | 16:9 | cover]",
        "",
        f"{title}这件事，表面看是一个新闻点，真正值得拆的是背后的信号。",
        "",
        fact_text,
    ]
    for section in sections[:4] if isinstance(sections, list) else []:
        heading = section.get("section", "")
        intent = section.get("intent", "补充关键信息")
        body.extend([
            "",
            f"## {heading}",
            "",
            f"这一部分要回答的是：{intent}。如果只看一句标题，很容易错过信息之间的先后关系。",
            "",
            "对读者来说，重点不是马上下结论，而是看清楚三个问题：谁在释放信号，信号指向哪里，以及后续还有哪些变量。",
        ])
    body.extend([
        "",
        f"> {title}的后续，关键在于公开信息如何继续落地。",
        "",
        f"[IMG: {title}的核心判断金句卡，深色背景，白色大字，适合公众号结尾传播 | 1:1 | card]",
    ])
    return "\n".join(body)
