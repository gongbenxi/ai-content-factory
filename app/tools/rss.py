"""RSS 抓取工具 — 从 skills/rss_fetcher 提取"""

from __future__ import annotations

import asyncio
from datetime import datetime

import feedparser

from app.tools.hotnews import HotItem

# 默认订阅源
DEFAULT_FEEDS = [
    "https://36kr.com/feed",
    "https://www.geekpark.net/rss",
    "https://feeds.feedburner.com/TechCrunch/",
]


async def fetch_rss_items(limit: int = 30, feeds: list[str] | None = None) -> list[HotItem]:
    """异步抓取 RSS 订阅源，返回统一的 HotItem 列表"""
    feeds = feeds or DEFAULT_FEEDS
    loop = asyncio.get_event_loop()
    items: list[HotItem] = []

    for feed_url in feeds:
        try:
            parsed = await loop.run_in_executor(None, _parse_feed, feed_url)
            now = datetime.now().isoformat()
            for entry in parsed[:limit]:
                items.append(HotItem(
                    rank=0,
                    title=entry.get("title", ""),
                    source="rss",
                    category=entry.get("source_name", ""),
                    url=entry.get("link", ""),
                    hot_score=0,
                    fetched_at=now,
                ))
        except Exception as e:
            print(f"[rss] 抓取失败 {feed_url}: {e}")

    return items[:limit]


def _parse_feed(url: str) -> list[dict]:
    """同步解析 RSS feed"""
    feed = feedparser.parse(url)
    source_name = feed.feed.get("title", url)
    return [
        {
            "title": entry.get("title", ""),
            "link": entry.get("link", ""),
            "source_name": source_name,
        }
        for entry in feed.entries
    ]
