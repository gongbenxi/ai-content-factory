"""
AI Content Factory - Phase 1 Multi-Agent Graph
============================================================

借鉴 GPT-Researcher 的 multi-agents 范式，实现 7 个 Agent 协同的内容生成流水线：
   Topic → Planner → Research(N parallel) → Editor → Writer → Illustrator → Reviewer ↔ Reviser

运行模式：
- 真 LLM 模式：设置 MIMO_API_KEY 环境变量即可用小米 MiMo 真实生成
- Mock 模式：不设 key 或加 --mock 参数，用 MockLLM 模拟（零依赖）
- 后续可切换为 Anthropic / OpenAI / DeepSeek，只需改环境变量

运行:
    cd ai-content-factory

    # 真 LLM 模式（需 pip install openai）
    export MIMO_API_KEY='your-key'
    python -m app.agents.graph

    # Mock 模式（零依赖）
    python -m app.agents.graph --mock
    python -m app.agents.graph --mock --revise-fail

    # 自定义请求
    python -m app.agents.graph --request "写一篇关于AI的小红书" --style "小红书种草" --platform xhs
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Awaitable, Callable

# ============================================================
# 1. State (LangGraph 中对应 TypedDict / pydantic.BaseModel)
# ============================================================
@dataclass
class ContentState:
    """流水线全程共享的状态对象。每个 Agent 读取自己关心的字段，写出自己的产出。"""

    # ---- 输入 ----
    user_request: str
    style_id: str = "caoz"
    target_platform: str = "wechat"
    user_preferences: dict = field(default_factory=dict)

    # ---- 中间产物 ----
    topic: dict | None = None
    outline: list[dict] | None = None
    sub_queries: list[str] | None = None
    snippets: list[dict] = field(default_factory=list)        # researcher 并发追加
    final_outline: dict | None = None
    draft_md: str | None = None
    image_prompts: list[dict] | None = None
    images: list[dict] = field(default_factory=list)

    # ---- 审阅闭环 ----
    review: dict | None = None
    revise_count: int = 0

    # ---- 元数据 ----
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    started_at: float = field(default_factory=time.time)
    events: list[dict] = field(default_factory=list)
    cost_cents: int = 0  # 累积成本（分）

    def emit(self, event_type: str, **data) -> None:
        """记录一个事件，同时实时打印（前端的 SSE 等价物）。"""
        evt = {
            "ts": round(time.time() - self.started_at, 2),
            "type": event_type,
            **data,
        }
        self.events.append(evt)
        # 控制台彩色简化版
        color = _EVENT_COLORS.get(event_type.split(".")[0], "\033[0m")
        ts_str = f"{evt['ts']:>6.2f}s"
        payload = json.dumps(data, ensure_ascii=False)
        if len(payload) > 100:
            payload = payload[:97] + "..."
        print(f"  {ts_str} {color}{event_type:<22}\033[0m {payload}")


_EVENT_COLORS = {
    "graph": "\033[1;35m",       # magenta bold
    "agent": "\033[1;36m",       # cyan bold
    "tool": "\033[0;33m",        # yellow
    "researcher": "\033[0;33m",
    "writer": "\033[0;32m",      # green
    "image": "\033[0;34m",       # blue
    "review": "\033[0;31m",      # red
    "error": "\033[1;31m",       # red bold
}


# ============================================================
# 2. LLM 抽象层（真 LLM + Mock 双模式）
# ============================================================
import os
import re

# 尝试导入真 LLM 客户端
try:
    from app.llm import LLMClient, create_llm
    _HAS_LLM_MODULE = True
except ImportError:
    _HAS_LLM_MODULE = False


class AgentLLM:
    """统一 LLM 接口：真 API 和 Mock 共用一个接口。

    Agent 代码只调 AgentLLM.call_json() / .call_text() / .stream()，
    底层自动路由到真 API 或 MockLLM。
    """

    def __init__(self, real_client=None, force_review_fail_first: bool = False):
        self._client = real_client  # LLMClient or None
        self._is_mock = real_client is None
        # mock 专用
        self._force_review_fail_first = force_review_fail_first
        self._review_call_count = 0

    @property
    def is_mock(self) -> bool:
        return self._is_mock

    async def call_json(self, agent: str, messages: list[dict], **kwargs) -> dict:
        """调用 LLM，期望返回 JSON dict。"""
        if self._is_mock:
            return await self._mock_call(agent)
        return await self._client.chat_json(agent, messages, **kwargs)

    async def call_text(self, agent: str, messages: list[dict], **kwargs) -> str:
        """调用 LLM，返回纯文本。"""
        if self._is_mock:
            mock_result = await self._mock_call(agent)
            return mock_result.get("raw_response", json.dumps(mock_result, ensure_ascii=False))
        return await self._client.chat(agent, messages, **kwargs)

    async def stream(self, agent: str, messages: list[dict], **kwargs):
        """流式输出，逐 chunk yield str。"""
        if self._is_mock:
            text = _MOCK_TEXTS.get(agent, "这是一段 mock 的流式输出文本。")
            for chunk in _chunk_text(text, size=8):
                await asyncio.sleep(0.015)
                yield chunk
            return
        async for chunk in self._client.stream(agent, messages, **kwargs):
            yield chunk

    async def _mock_call(self, agent: str) -> dict:
        """Mock 模式：根据 agent 名返回预制 JSON，模拟延迟。"""
        await asyncio.sleep(0.2 + random.random() * 0.4)
        if agent == "reviewer":
            self._review_call_count += 1
            if self._force_review_fail_first and self._review_call_count == 1:
                return _MOCK["reviewer_fail"]
        return _MOCK.get(agent, {"raw_response": f"mock response for {agent}"})


def _chunk_text(text: str, size: int = 8):
    for i in range(0, len(text), size):
        yield text[i : i + size]


# ---- Mock 数据（--mock 模式使用）----
_MOCK = {
    "topic": {
        "title": "DeepSeek-V3 发布带来的国产大模型竞争格局变化",
        "angle": "技术拐点 + 商业影响双线",
        "target_platform": "wechat",
        "hook": "六百万美元，把硅谷震了",
    },
    "planner": {
        "outline": [
            {"section": "DeepSeek-V3 性能数据", "intent": "建立技术事实"},
            {"section": "对比 GPT-4o 和 Claude Sonnet", "intent": "横向参照"},
            {"section": "对国内创业公司的冲击", "intent": "商业视角"},
            {"section": "二级市场反应", "intent": "佐证"},
            {"section": "未来 3 个月预测", "intent": "结论"},
        ],
        "sub_queries": [
            "DeepSeek-V3 在 MMLU/HumanEval 等基准的具体得分",
            "DeepSeek 训练成本和开源协议",
            "DeepSeek 发布后 OpenAI 和 Anthropic 的反应",
            "中国 AI 创业公司对开源模型的态度变化",
            "A 股和港股 AI 概念股近期波动",
        ],
    },
    "editor": {
        "final_outline": {
            "sections": [
                {"section": "DeepSeek-V3 性能数据", "cite_snippet_ids": [0, 1], "target_words": 350},
                {"section": "对比 GPT-4o 和 Claude Sonnet", "cite_snippet_ids": [2, 3], "target_words": 400},
                {"section": "对国内创业公司的冲击", "cite_snippet_ids": [4, 5, 6], "target_words": 500},
                {"section": "二级市场反应", "cite_snippet_ids": [7, 8], "target_words": 300},
                {"section": "未来 3 个月预测", "cite_snippet_ids": [9], "target_words": 250},
            ],
        },
        "style_adjustments": "保留 caoz 短句节奏；段落首句作为强观点钩子",
    },
    "writer": {
        "image_prompts": [
            {"para_id": 1, "prompt": "DeepSeek-V3 在 MMLU/HumanEval 等基准对比 GPT-4o 的柱状图", "ratio": "16:9"},
            {"para_id": 3, "prompt": "国内外 AI 公司估值对比示意图，简约商务风", "ratio": "16:9"},
            {"para_id": 5, "prompt": "未来 3 个月 AI 行业关键节点时间轴", "ratio": "1:1"},
        ],
    },
    "reviewer": {
        "pass": True,
        "score": 8.4,
        "issues": [],
        "summary": "事实引用完整，风格匹配良好，图文一致性 OK。",
    },
    "reviewer_fail": {
        "pass": False,
        "score": 6.8,
        "issues": [
            {"type": "image_mismatch", "para_id": 2, "detail": "图描绘的是发布会，但段落讲商业影响"},
            {"type": "style_drift", "detail": "结尾过于客观，原作者偏煽情/反问"},
        ],
        "summary": "图文有 1 处不一致；结尾风格偏离。需修订。",
    },
    "reviser": {
        "summary": "已按 reviewer 反馈修订：替换段落 2 的图占位符；结尾改为反问句收尾。",
    },
}

_MOCK_TEXTS = {
    "writer": (
        "# DeepSeek 这次的发布，让所有人都不淡定了\n\n"
        "这两天科技圈最炸的消息，不是 OpenAI，也不是谷歌。是 DeepSeek。\n\n"
        "一家杭州公司，把性能跟 GPT-4o 接近的模型，开源了。还告诉你训练成本只用了 600 万美元。\n\n"
        "六百万美元什么概念？OpenAI 训 GPT-4 烧了一亿美元起步——而且人家还不开源。\n\n"
        "[IMG: DeepSeek-V3 在 MMLU/HumanEval 等基准对比 GPT-4o 的柱状图 | 16:9]\n\n"
        "这就是为什么过去 48 小时，硅谷一片哀嚎。Anthropic 的 Sonnet 4.6 周二刚发，今天直接被 DeepSeek 抢了头条。\n\n"
        "## 国内创业公司，可能要变天\n\n"
        "过去两年，国内大模型创业公司有个共同的痛点：自己训不出 SOTA 模型，调 OpenAI 又被卡，调国内闭源大厂又贵。\n\n"
        "[IMG: 国内外 AI 公司估值对比示意图，简约商务风 | 16:9]\n\n"
        "现在 DeepSeek 把基线拉到一个新位置——而且开源、便宜、够用。\n\n"
        "## 未来三个月会发生什么\n\n"
        "[IMG: 未来 3 个月 AI 行业关键节点时间轴 | 1:1]\n\n"
        "一句话收尾：技术领先三个月不算什么，重要的是，谁能把这三个月的窗口期变成商业护城河？\n"
    ),
}


# ============================================================
# 2b. Agent Prompts（真 LLM 模式下的提示词）
# ============================================================
PROMPTS = {
    "topic_system": """你是一个资深内容策划。根据当日热榜新闻和用户偏好，选出最值得写的 1 个选题。
输出纯 JSON（不要 markdown 包裹），格式：
{
  "title": "选题标题",
  "angle": "切入角度",
  "target_platform": "目标平台",
  "hook": "开头钩子（一句话）"
}""",

    "planner_system": """你是一个内容大纲规划师。根据选题，生成文章大纲和研究子查询。
要求：
- outline: 3~6 个 section，每个有 section 名和 intent
- sub_queries: 3~5 个搜索查询（用于后续研究员去搜索事实素材）

输出纯 JSON：
{
  "outline": [{"section": "...", "intent": "..."}],
  "sub_queries": ["查询1", "查询2", ...]
}""",

    "editor_system": """你是一个资深编辑。根据大纲和收集到的素材片段，生成最终写作大纲。
要求：
- 决定每节引用哪几条 snippet（通过 index）
- 设定每节目标字数
- 输出风格调整建议

输出纯 JSON：
{
  "final_outline": {
    "sections": [
      {"section": "标题", "cite_snippet_ids": [0, 1], "target_words": 400}
    ]
  },
  "style_adjustments": "风格调整建议"
}""",

    "writer_system": """你是一个顶尖中文写手。根据大纲、素材和风格要求写一篇完整文章。

写作规则：
1. 严格模仿给定的风格指纹（句式、节奏、用词偏好）
2. 每引用一个事实必须基于给定素材，不可编造
3. 在需要配图的地方插入占位符：[IMG: 场景描述 | 比例]
4. 控制全文字数在目标范围内

直接输出 markdown 格式的文章正文，不需要 JSON 包裹。""",

    "writer_image_prompts_system": """从下面的文章草稿中提取所有 [IMG: ... | ...] 占位符，生成配图 prompt 列表。
输出纯 JSON：
{
  "image_prompts": [
    {"para_id": 1, "prompt": "图片描述", "ratio": "16:9"}
  ]
}""",

    "reviewer_system": """你是一个严格的内容审阅者。审查文章的以下维度并打分：
1. 事实准确性（是否有编造内容）
2. 风格匹配度（是否符合目标风格）
3. 图文一致性（配图占位符是否与段落内容匹配）
4. 平台规范（字数、格式是否符合目标平台）

输出纯 JSON：
{
  "pass": true/false,
  "score": 0-10,
  "issues": [{"type": "issue_type", "detail": "描述"}],
  "summary": "总结"
}

通过条件：score >= 7.5 且无严重 issue。""",

    "reviser_system": """你是一个修订编辑。根据审阅意见修改文章，只改有问题的部分，不要重写全文。
输出修改后的完整文章 markdown。在末尾追加一行 JSON 注释：
<!-- REVISE_META: {"summary": "修改了什么"} -->""",
}


# ============================================================
# 3. Mock Tools (在生产中替换为真实实现)
# ============================================================
async def tool_fetch_hotnews_unified(sources: list[str], limit: int = 30) -> list[dict]:
    """聚合调用 6 个采集 skill。生产中：subprocess 调 skills/{src}/scripts/save_to_db.py"""
    await asyncio.sleep(0.3)
    return [
        {"source": "weibo", "title": "DeepSeek-V3 开源 性能炸裂", "url": "https://m.weibo.cn/...", "rank": 1},
        {"source": "zhihu", "title": "如何评价 DeepSeek-V3 的发布", "url": "https://zhihu.com/...", "rank": 2},
        {"source": "baidu", "title": "国产大模型再下一城", "url": "https://baidu.com/...", "rank": 3},
        # ... mock 截断
    ][:limit]


async def tool_web_search(query: str, k: int = 5) -> list[dict]:
    """生产中：tavily.search(query, max_results=k)"""
    await asyncio.sleep(0.4 + random.random() * 0.3)
    return [
        {
            "url": f"https://example.com/{abs(hash(query + str(i))) % 100000}",
            "title": f"[{query[:20]}] - 文章 {i + 1}",
            "snippet": f"关于 {query} 的相关内容片段 {i + 1}...",
        }
        for i in range(k)
    ]


async def tool_scrape_url(url: str) -> str:
    """生产中：crawl4ai.AsyncWebCrawler().arun(url, output_format='markdown')"""
    await asyncio.sleep(0.3 + random.random() * 0.4)
    return f"[scraped from {url}] " + "lorem ipsum dolor sit amet " * 10


async def tool_vector_search_history(query: str, k: int = 5) -> list[dict]:
    """生产中：pgvector cosine 检索 articles + snippets"""
    await asyncio.sleep(0.1)
    return []  # mock：假装没有历史


async def tool_gen_image(prompt: str, ratio: str = "16:9") -> str:
    """生产中：调 image-gen-coze skill 或 Flux/Recraft API"""
    await asyncio.sleep(0.5 + random.random() * 0.5)
    return f"https://mock-cdn.example.com/img/{abs(hash(prompt)) % 100000}.png"


async def tool_content_safety_check(text: str) -> dict:
    """生产中：阿里云内容安全 API"""
    await asyncio.sleep(0.1)
    return {"pass": True, "issues": []}


async def tool_image_consistency_check(image_url: str, paragraph: str) -> dict:
    """生产中：Claude Vision / Qwen-VL 看图判断"""
    await asyncio.sleep(0.2)
    score = 0.75 + random.random() * 0.2
    return {"consistent": score > 0.7, "score": round(score, 2)}


async def tool_load_style_fingerprint(style_id: str) -> dict:
    """生产中：subprocess 调 skills/style_fingerprint/style_fingerprint.py show <style_id>"""
    await asyncio.sleep(0.05)
    return {
        "style_id": style_id,
        "syntax_patterns": {"avg_sentence_len": 14.3, "rhetorical_question_rate": 0.128},
        "top_words": ["商业", "逻辑", "本质", "所以", "核心"],
        "rhetorical_features": ["短句", "反问", "口语化", "观点强烈"],
        "examples": [
            "所以问题来了：用户真的需要这个吗？",
            "商业的本质从来没变，只是叙事换了一种。",
        ],
    }


# ============================================================
# 4. Agent 实现
# ============================================================
async def topic_agent(state: ContentState, llm: AgentLLM) -> ContentState:
    state.emit("agent.start", agent="topic")
    news = await tool_fetch_hotnews_unified(["weibo", "zhihu", "baidu"], limit=30)
    state.emit("tool.call", tool="fetch_hotnews_unified", returned=len(news))
    history = await tool_vector_search_history(state.user_request, k=5)
    state.emit("tool.call", tool="vector_search_history", returned=len(history))

    messages = [
        {"role": "system", "content": PROMPTS["topic_system"]},
        {"role": "user", "content": f"用户指令：{state.user_request}\n\n当日热榜：{json.dumps(news, ensure_ascii=False)}\n\n历史素材：{json.dumps(history, ensure_ascii=False)}"},
    ]
    state.topic = await llm.call_json("topic", messages)
    state.cost_cents += 4
    state.emit("agent.done", agent="topic", title=state.topic["title"])
    return state


async def planner_agent(state: ContentState, llm: AgentLLM) -> ContentState:
    state.emit("agent.start", agent="planner")
    messages = [
        {"role": "system", "content": PROMPTS["planner_system"]},
        {"role": "user", "content": f"选题：{json.dumps(state.topic, ensure_ascii=False)}\n目标平台：{state.target_platform}"},
    ]
    result = await llm.call_json("planner", messages)
    state.outline = result["outline"]
    state.sub_queries = result["sub_queries"]
    state.cost_cents += 6
    state.emit(
        "agent.done",
        agent="planner",
        outline_sections=len(state.outline),
        sub_queries=len(state.sub_queries),
    )
    return state


async def researcher_worker(query: str, query_idx: int, state: ContentState) -> list[dict]:
    """单个 researcher worker。N 个并发执行。"""
    state.emit("researcher.start", q_idx=query_idx, query=query)
    web = await tool_web_search(query, k=5)
    snippets = []
    for r in web[:3]:
        text = await tool_scrape_url(r["url"])
        snippets.append(
            {
                "source": r["url"],
                "title": r["title"],
                "excerpt": text[:200],
                "credibility": round(0.7 + random.random() * 0.25, 2),
                "angle": random.choice(["背景", "数据", "案例", "观点", "趋势"]),
                "from_query": query_idx,
            }
        )
    state.emit("researcher.done", q_idx=query_idx, snippets=len(snippets))
    return snippets


async def research_dispatcher(state: ContentState, llm: AgentLLM) -> ContentState:
    """并行 fan-out：N 个 sub_query → N 个 worker 同时跑。这是 GPT-Researcher 提速的关键。"""
    state.emit("agent.start", agent="research", parallel=len(state.sub_queries))
    workers = [
        researcher_worker(q, idx, state)
        for idx, q in enumerate(state.sub_queries)
    ]
    results = await asyncio.gather(*workers)
    for batch in results:
        state.snippets.extend(batch)
    state.cost_cents += 2 * len(state.sub_queries)  # haiku 每 worker 便宜
    state.emit("agent.done", agent="research", total_snippets=len(state.snippets))
    return state


async def editor_agent(state: ContentState, llm: AgentLLM) -> ContentState:
    state.emit("agent.start", agent="editor")
    fp = await tool_load_style_fingerprint(state.style_id)
    state.emit("tool.call", tool="load_style_fingerprint", style_id=fp["style_id"])
    messages = [
        {"role": "system", "content": PROMPTS["editor_system"]},
        {"role": "user", "content": (
            f"原始大纲：{json.dumps(state.outline, ensure_ascii=False)}\n\n"
            f"素材片段（共 {len(state.snippets)} 条）：{json.dumps(state.snippets[:20], ensure_ascii=False)}\n\n"
            f"风格指纹：{json.dumps(fp, ensure_ascii=False)}"
        )},
    ]
    result = await llm.call_json("editor", messages)
    state.final_outline = result["final_outline"]
    state.cost_cents += 8
    state.emit("agent.done", agent="editor", sections=len(state.final_outline["sections"]))
    return state


async def writer_agent(state: ContentState, llm: AgentLLM) -> ContentState:
    state.emit("agent.start", agent="writer", model="mimo-v2.5-pro", cache="hit")

    # 加载风格指纹用于写作
    fp = await tool_load_style_fingerprint(state.style_id)

    # 收集被引用的 snippets
    cited_ids = set()
    if state.final_outline:
        for sec in state.final_outline.get("sections", []):
            cited_ids.update(sec.get("cite_snippet_ids", []))
    cited_snippets = [state.snippets[i] for i in sorted(cited_ids) if i < len(state.snippets)]

    messages = [
        {"role": "system", "content": PROMPTS["writer_system"]},
        {"role": "user", "content": (
            f"风格指纹：{json.dumps(fp, ensure_ascii=False)}\n\n"
            f"最终大纲：{json.dumps(state.final_outline, ensure_ascii=False)}\n\n"
            f"引用素材：{json.dumps(cited_snippets, ensure_ascii=False)}\n\n"
            f"目标平台：{state.target_platform}"
        )},
    ]

    # 流式写作
    chunks: list[str] = []
    async for chunk in llm.stream("writer", messages):
        chunks.append(chunk)
    state.draft_md = "".join(chunks)

    # 提取配图 prompt
    img_messages = [
        {"role": "system", "content": PROMPTS["writer_image_prompts_system"]},
        {"role": "user", "content": f"文章草稿：\n\n{state.draft_md}"},
    ]
    meta = await llm.call_json("writer", img_messages)
    state.image_prompts = meta.get("image_prompts", [])
    state.cost_cents += 45  # writer 最贵，但 prompt cache 已计入
    state.emit(
        "agent.done",
        agent="writer",
        words=len(state.draft_md),
        image_prompts=len(state.image_prompts),
    )
    return state


async def illustrator_agent(state: ContentState, llm: AgentLLM) -> ContentState:
    state.emit("agent.start", agent="illustrator", count=len(state.image_prompts))
    images = []
    for ip in state.image_prompts:
        url = await tool_gen_image(ip["prompt"], ip["ratio"])
        img = {
            "para_id": ip["para_id"],
            "url": url,
            "prompt": ip["prompt"],
            "ratio": ip["ratio"],
        }
        images.append(img)
        state.emit("image.generated", url=url, ratio=ip["ratio"])
    state.images = images
    state.cost_cents += 20 * len(images)
    state.emit("agent.done", agent="illustrator", generated=len(images))
    return state


async def reviewer_agent(state: ContentState, llm: AgentLLM) -> ContentState:
    round_num = state.revise_count + 1
    state.emit("agent.start", agent="reviewer", round=round_num)

    safety = await tool_content_safety_check(state.draft_md or "")
    state.emit("tool.call", tool="content_safety_check", **safety)

    consistency_scores = []
    for img in state.images:
        c = await tool_image_consistency_check(img["url"], "")
        consistency_scores.append(c["score"])
    avg_consistency = (
        round(sum(consistency_scores) / max(len(consistency_scores), 1), 2)
        if consistency_scores
        else 0
    )
    state.emit("tool.call", tool="image_consistency_check", avg=avg_consistency)

    messages = [
        {"role": "system", "content": PROMPTS["reviewer_system"]},
        {"role": "user", "content": (
            f"审阅轮次：第 {round_num} 轮\n\n"
            f"文章草稿：\n{state.draft_md}\n\n"
            f"配图信息：{json.dumps(state.images, ensure_ascii=False)}\n\n"
            f"内容安全检查结果：{json.dumps(safety, ensure_ascii=False)}\n\n"
            f"图文一致性均分：{avg_consistency}"
        )},
    ]
    review = await llm.call_json("reviewer", messages)
    state.review = review
    state.cost_cents += 12
    state.emit(
        "review.done",
        passed=review["pass"],
        score=review["score"],
        issues=len(review["issues"]),
    )
    return state


async def reviser_agent(state: ContentState, llm: AgentLLM) -> ContentState:
    state.emit("agent.start", agent="reviser", round=state.revise_count + 1)
    messages = [
        {"role": "system", "content": PROMPTS["reviser_system"]},
        {"role": "user", "content": (
            f"当前草稿：\n{state.draft_md}\n\n"
            f"审阅意见：{json.dumps(state.review['issues'], ensure_ascii=False)}"
        )},
    ]
    revised_md = await llm.call_text("reviser", messages)
    state.draft_md = revised_md
    state.revise_count += 1
    state.cost_cents += 10
    state.emit("agent.done", agent="reviser", round=state.revise_count, summary="修订完成")
    return state


# ============================================================
# 5. Graph orchestrator
# 在生产中替换为 LangGraph StateGraph (见文件末尾对照)
# ============================================================
MAX_REVISE_ROUNDS = 2


async def run_graph(initial: ContentState, llm: AgentLLM) -> ContentState:
    """主流水线。每个 await 边对应 LangGraph 的一条 edge。"""
    initial.emit(
        "graph.start",
        run_id=initial.run_id,
        request=initial.user_request[:60],
        style=initial.style_id,
        platform=initial.target_platform,
    )

    state = await topic_agent(initial, llm)
    state = await planner_agent(state, llm)
    state = await research_dispatcher(state, llm)
    state = await editor_agent(state, llm)
    state = await writer_agent(state, llm)
    state = await illustrator_agent(state, llm)
    state = await reviewer_agent(state, llm)

    # 条件边：review.pass → END，否则 → revise → review (loop)
    while not state.review["pass"] and state.revise_count < MAX_REVISE_ROUNDS:
        state = await reviser_agent(state, llm)
        state = await reviewer_agent(state, llm)

    final_status = "done" if state.review["pass"] else "needs_human"
    state.emit(
        "graph.done",
        status=final_status,
        words=len(state.draft_md or ""),
        images=len(state.images),
        revise_rounds=state.revise_count,
        cost_cents=state.cost_cents,
        elapsed_s=round(time.time() - state.started_at, 2),
    )
    return state


# ============================================================
# 6. CLI 入口
# ============================================================
def _print_summary(state: ContentState) -> None:
    print()
    print("=" * 64)
    print(f"  RUN SUMMARY  ·  run_id = {state.run_id}")
    print("=" * 64)
    print(f"  Topic         : {state.topic['title'] if state.topic else '(none)'}")
    print(f"  Sub-queries   : {len(state.sub_queries or [])}")
    print(f"  Snippets      : {len(state.snippets)}")
    print(f"  Outline       : {len(state.outline or [])} → final {len(state.final_outline['sections']) if state.final_outline else 0}")
    print(f"  Draft         : {len(state.draft_md or ''):>5} chars")
    print(f"  Images        : {len(state.images)}")
    rev = state.review or {}
    print(f"  Review        : pass={rev.get('pass')} score={rev.get('score')} issues={len(rev.get('issues', []))}")
    print(f"  Revise rounds : {state.revise_count}")
    print(f"  Total events  : {len(state.events)}")
    print(f"  Cost          : ¥{state.cost_cents / 100:.2f}")
    print(f"  Elapsed       : {time.time() - state.started_at:.2f}s")
    print("=" * 64)


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="AI Content Factory · multi-agent skeleton")
    p.add_argument("--request", default="今天 AI 圈有什么值得写的？写一篇模仿 caoz 风格的公众号文")
    p.add_argument("--style", default="caoz")
    p.add_argument("--platform", default="wechat", choices=["wechat", "xhs", "weibo", "zhihu"])
    p.add_argument("--mock", action="store_true", help="使用 MockLLM 模式（零依赖）")
    p.add_argument("--revise-fail", action="store_true", help="模拟首轮 review 不通过 → 触发修订")
    p.add_argument("--json", action="store_true", help="末尾输出完整 state JSON")
    return p.parse_args()


async def main() -> None:
    args = _parse_args()

    # 创建 LLM 客户端：--mock 或缺 key 时降级 Mock，否则用真 MiMo API
    real_client = None if args.mock else create_llm()
    llm = AgentLLM(real_client=real_client, force_review_fail_first=args.revise_fail)
    mode = "Mock" if llm.is_mock else "MiMo API"

    print()
    print("\033[1;35m▶ AI Content Factory · Multi-Agent Dry Run\033[0m")
    print(f"  mode     : {mode}")
    print(f"  request  : {args.request}")
    print(f"  style    : {args.style}")
    print(f"  platform : {args.platform}")
    print(f"  revise   : {'will fail first round' if args.revise_fail else 'pass on first round'}")
    print()

    initial = ContentState(
        user_request=args.request,
        style_id=args.style,
        target_platform=args.platform,
    )
    state = await run_graph(initial, llm)
    _print_summary(state)

    if args.json:
        print()
        print("=== STATE (JSON) ===")
        # events 单独压缩输出
        d = asdict(state)
        d["events_summary"] = f"<{len(d.pop('events'))} events>"
        print(json.dumps(d, ensure_ascii=False, indent=2)[:2000])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\033[1;31m✗ Interrupted\033[0m")
        sys.exit(130)


# ============================================================
# 7. 迁移到真 LangGraph 的对照模板（注释，运行不会执行）
# ============================================================
"""
# pip install langgraph langchain-anthropic psycopg[binary]

from typing import TypedDict, Annotated
from operator import add
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Send

class GraphState(TypedDict):
    user_request: str
    style_id: str
    target_platform: str
    topic: dict
    outline: list
    sub_queries: list
    snippets: Annotated[list, add]   # reducer：并发追加
    final_outline: dict
    draft_md: str
    image_prompts: list
    images: list
    review: dict
    revise_count: int

g = StateGraph(GraphState)
g.add_node("topic", topic_agent)
g.add_node("planner", planner_agent)
g.add_node("researcher_worker", researcher_worker)
g.add_node("editor", editor_agent)
g.add_node("writer", writer_agent)
g.add_node("illustrator", illustrator_agent)
g.add_node("reviewer", reviewer_agent)
g.add_node("reviser", reviser_agent)

g.set_entry_point("topic")
g.add_edge("topic", "planner")

# fan-out：dispatcher 不是 node，是返回 Send 列表
def research_dispatch(state: GraphState):
    return [
        Send("researcher_worker", {"query": q, "query_idx": i})
        for i, q in enumerate(state["sub_queries"])
    ]
g.add_conditional_edges("planner", research_dispatch, ["researcher_worker"])

# fan-in：所有 worker 完成后聚合到 editor
g.add_edge("researcher_worker", "editor")
g.add_edge("editor", "writer")
g.add_edge("writer", "illustrator")
g.add_edge("illustrator", "reviewer")

# 条件边：review.pass=True → END；否则 → reviser（最多 2 轮）
def review_gate(state: GraphState):
    if state["review"]["pass"]:
        return "done"
    if state["revise_count"] >= 2:
        return "done"  # needs_human, 留给前端处理
    return "revise"
g.add_conditional_edges("reviewer", review_gate, {"done": END, "revise": "reviser"})
g.add_edge("reviser", "reviewer")

# 持久化 checkpoint：断点续跑、人工介入、回放都靠它
checkpointer = PostgresSaver.from_conn_string("postgresql://...")
graph = g.compile(checkpointer=checkpointer)

# 调用
config = {"configurable": {"thread_id": "run-7a3f9c2b"}}
async for event in graph.astream({"user_request": "...", "style_id": "caoz", ...}, config):
    print(event)  # 推到 SSE
"""
