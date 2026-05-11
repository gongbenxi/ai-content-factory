"""
热点新闻工具 — 聚合百度热搜（Phase 1）+ RSS 订阅源
================================================================
供 TopicAgent 调用，获取当前热点作为选题素材。

数据来源：
  - 百度实时热搜 API（top.baidu.com）
  - RSS 订阅源（Phase 1.2 集成）

用法：
  topics = await fetch_hotnews(limit=30)
  topics = await fetch_hotnews(limit=30, sources=["baidu", "rss"])
"""

from __future__ import annotations

import json
import asyncio
import urllib.request
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

class HotItem:
    """统一热点条目"""
    __slots__ = ("rank", "title", "source", "category", "url", "hot_score", "fetched_at")

    def __init__(
        self,
        rank: int,
        title: str,
        source: str,
        category: str = "",
        url: str = "",
        hot_score: int = 0,
        fetched_at: str = "",
    ):
        self.rank = rank
        self.title = title
        self.source = source
        self.category = category
        self.url = url
        self.hot_score = hot_score
        self.fetched_at = fetched_at or datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "title": self.title,
            "source": self.source,
            "category": self.category,
            "url": self.url,
            "hot_score": self.hot_score,
            "fetched_at": self.fetched_at,
        }


# ---------------------------------------------------------------------------
# 百度热搜
# ---------------------------------------------------------------------------

_BAIDU_API = "https://top.baidu.com/api/board?platform=wise&tab=realtime"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://top.baidu.com/",
}


def _fetch_baidu_sync(limit: int = 50) -> list[HotItem]:
    """同步请求百度热搜 API（将在线程池中调用）。"""
    req = urllib.request.Request(_BAIDU_API, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    if not data.get("success") or "data" not in data:
        raise RuntimeError("百度热搜 API 返回格式异常")

    cards = data["data"].get("cards", [])
    if not cards:
        raise RuntimeError("百度热搜无卡片数据")

    # 嵌套解析: cards[].content[].content[]
    raw_items: list[dict] = []
    for card in cards:
        if "content" in card and isinstance(card["content"], list):
            for content_item in card["content"]:
                if "content" in content_item and isinstance(content_item["content"], list):
                    raw_items.extend(content_item["content"])

    if not raw_items:
        raise RuntimeError("百度热搜内容为空")

    now = datetime.now().isoformat()
    results: list[HotItem] = []
    for item in raw_items[:limit]:
        title = item.get("word", "").strip()
        if not title:
            continue

        # 标签解析
        hot_tag = item.get("hotTag", "0")
        label = ""
        if item.get("labelTag"):
            label = item["labelTag"].get("day", {}).get("text", "")

        if label:
            category = label
        elif hot_tag == "1":
            category = "新"
        elif hot_tag == "3":
            category = "热"
        else:
            category = "综合"

        results.append(HotItem(
            rank=item.get("index", 0),
            title=title,
            source="baidu",
            category=category,
            url=f"https://www.baidu.com/s?wd={title}",
            hot_score=int(item.get("hotScore", 0) or 0),
            fetched_at=now,
        ))

    return results


async def fetch_baidu_hot(limit: int = 30) -> list[HotItem]:
    """异步获取百度热搜（在线程池执行同步 HTTP）。"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch_baidu_sync, limit)


# ---------------------------------------------------------------------------
# 统一入口
# ---------------------------------------------------------------------------

async def fetch_hotnews(
    limit: int = 30,
    sources: Optional[list[str]] = None,
) -> list[dict]:
    """
    聚合获取热点新闻。

    Args:
        limit: 每个来源最多返回条数
        sources: 数据源列表，默认 ["baidu"]。Phase 1.2 加入 "rss"。

    Returns:
        统一格式的热点列表 (list of dict)
    """
    if sources is None:
        sources = ["baidu"]

    tasks = []
    if "baidu" in sources:
        tasks.append(fetch_baidu_hot(limit))
    # RSS
    if "rss" in sources:
        from app.tools.rss import fetch_rss_items
        tasks.append(fetch_rss_items(limit))

    all_items: list[HotItem] = []
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            # 单源失败不影响整体，降级处理
            print(f"[hotnews] 数据源获取失败: {result}")
            continue
        all_items.extend(result)

    # 按 hot_score 降序排列
    all_items.sort(key=lambda x: x.hot_score, reverse=True)

    return [item.to_dict() for item in all_items]


# 统一入口别名（PRD §4.2 中 TopicAgent 调用）
async def fetch_hotnews_unified(limit: int = 30, sources: Optional[list[str]] = None) -> list[dict]:
    """统一热点采集入口，聚合百度热搜 + RSS"""
    return await fetch_hotnews(limit=limit, sources=sources or ["baidu", "rss"])


# ---------------------------------------------------------------------------
# CLI 测试入口
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    async def _main():
        limit = int(sys.argv[1]) if len(sys.argv) > 1 else 20
        items = await fetch_hotnews(limit=limit)
        print(f"\n获取到 {len(items)} 条热点：\n")
        for item in items[:20]:
            print(f"  {item['rank']:>2}. [{item['category']}] {item['title']}")
        print(f"\n  ... 共 {len(items)} 条")

    asyncio.run(_main())
