"""Web 搜索工具 — Tavily API 封装"""

from __future__ import annotations

import os


async def web_search(query: str, k: int = 5) -> list[dict]:
    """调用 Tavily API 搜索网页，返回 [{url, title, content, score}]"""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return [{"url": "", "title": f"[mock] {query}", "content": f"mock search result for: {query}", "score": 0.5}]

    from tavily import TavilyClient
    client = TavilyClient(api_key=api_key)
    results = client.search(query, max_results=k, search_depth="basic")

    return [
        {
            "url": r["url"],
            "title": r.get("title", ""),
            "content": r.get("content", ""),
            "score": r.get("score", 0),
        }
        for r in results.get("results", [])
    ]
