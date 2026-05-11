"""ResearcherAgent — 研究：并行调采集器+网页抓取

每个 worker 处理一个 sub_query，通过 Send API fan-out。
"""

from __future__ import annotations

import json
from pathlib import Path

from app.llm.client import LLMClient
from app.tools.search import web_search
from app.tools.scraper import scrape_url
from app.workers.runner import emit_event

_PROMPT = (Path(__file__).resolve().parents[1] / "llm" / "prompts" / "researcher.txt").read_text()


async def researcher_worker(state: dict, config=None) -> dict:
    """LangGraph node: ResearcherAgent (单个 worker)"""
    configurable = config.get("configurable", {}) if config else {}
    mock = configurable.get("mock", False)
    run_id = configurable.get("run_id") or state.get("run_id", "")
    budget = configurable.get("budget")

    query = state.get("query", "")

    await emit_event(run_id, "agent.start", {"agent": "researcher", "query": query[:50]})

    if not query:
        await emit_event(run_id, "agent.done", {"agent": "researcher", "snippets": 0})
        return {"snippets": []}

    search_results = await web_search(query, k=5)
    await emit_event(run_id, "tool.call", {"agent": "researcher", "tool": "web_search", "query": query[:50], "results": len(search_results)})

    scraped = []
    for r in search_results[:3]:
        if r.get("url"):
            await emit_event(run_id, "tool.call", {"agent": "researcher", "tool": "scrape_url", "url": r["url"][:100]})
            content = await scrape_url(r["url"])
            if content.get("success"):
                scraped.append(content)

    llm = LLMClient(run_id=run_id, budget=budget)
    context = json.dumps({
        "query": query,
        "search_results": search_results,
        "scraped": [{"url": s["url"], "markdown": s["markdown"][:500]} for s in scraped],
    }, ensure_ascii=False)

    messages = [
        {"role": "system", "content": _PROMPT},
        {"role": "user", "content": f"子问题: {query}\n\n搜索结果和抓取内容:\n{context}"},
    ]

    result, usage = await llm.chat_json("researcher", messages, mock=mock)

    if isinstance(result, list):
        snippets = result
    elif isinstance(result, dict) and "snippets" in result:
        snippets = result["snippets"]
    else:
        snippets = []

    await emit_event(run_id, "agent.done", {
        "agent": "researcher",
        "snippets": len(snippets),
        "usage": usage,
    })

    return {
        "snippets": snippets,
        "cost_cents": usage.get("cost_cents", 0),
        "usage_by_agent": {"researcher": {
            "input_tokens": usage.get("input_tokens", 0),
            "output_tokens": usage.get("output_tokens", 0),
            "cost_cents": usage.get("cost_cents", 0),
        }},
    }
