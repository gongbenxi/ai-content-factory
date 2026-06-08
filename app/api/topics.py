"""Topics API — 选题候选"""

from __future__ import annotations

import logging
from datetime import datetime
from fastapi import APIRouter

logger = logging.getLogger(__name__)
router = APIRouter()

# 缓存最近一次刷新结果
_cache: dict = {"items": [], "fetched_at": None, "refresh_id": 0, "visible_titles": []}


def _dedupe_items(items: list[dict]) -> list[dict]:
    seen: set[str] = set()
    deduped: list[dict] = []
    for item in items:
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        key = title.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _decorate_items(items: list[dict]) -> list[dict]:
    decorated: list[dict] = []
    for idx, item in enumerate(items):
        hot_score = int(item.get("hot_score") or item.get("hot") or 0)
        decorated.append({
            **item,
            "rank": item.get("rank") or idx + 1,
            "hot_score": hot_score,
            "platform": item.get("platform") or "wechat",
            "target_platform": item.get("target_platform") or "wechat",
            "quality": item.get("quality") or item.get("estimated_quality") or 0.75,
            "angle": item.get("angle") or _default_angle(item),
        })
    return decorated


def _default_angle(item: dict) -> str:
    source = item.get("source") or "hot"
    category = item.get("category") or "热点"
    if source == "rss":
        return f"{category} · 行业观察"
    return f"{category} · 热点解读"


def _source_counts(items: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        source = str(item.get("source") or "unknown")
        counts[source] = counts.get(source, 0) + 1
    return counts


def _visible_window(items: list[dict], refresh_id: int, size: int = 5) -> list[dict]:
    if not items:
        return []
    if len(items) <= size:
        return items
    start = ((max(refresh_id, 1) - 1) * size) % len(items)
    window = items[start:start + size]
    if len(window) < size:
        window.extend(items[:size - len(window)])
    return window


async def _fetch_topic_items(limit: int = 30) -> list[dict]:
    from app.tools.hotnews import fetch_hotnews_unified

    items = await fetch_hotnews_unified(limit=limit, sources=["baidu", "rss"])
    return _decorate_items(_dedupe_items(items))


def _response(candidates: list[dict], *, cached: bool, refreshed: bool = False, error: str | None = None) -> dict:
    return {
        "candidates": candidates,
        "cached": cached,
        "refreshed": refreshed,
        "count": len(_cache["items"]),
        "fetched_at": _cache["fetched_at"],
        "refresh_id": _cache["refresh_id"],
        "source_counts": _source_counts(_cache["items"]),
        "error": error,
    }


@router.get("/candidates")
async def get_candidates():
    """今日候选选题"""
    if _cache["items"]:
        candidates = _visible_window(_cache["items"], max(_cache["refresh_id"], 1))
        return _response(candidates, cached=True)
    try:
        items = await _fetch_topic_items(limit=30)
        _cache["items"] = items
        _cache["fetched_at"] = datetime.utcnow().isoformat()
        _cache["refresh_id"] = 1
        candidates = _visible_window(items, _cache["refresh_id"])
        _cache["visible_titles"] = [item["title"] for item in candidates]
        return _response(candidates, cached=False)
    except Exception as e:
        return _response([], cached=False, error=str(e))


@router.post("/refresh")
async def refresh_candidates():
    """强制刷新选题（重新抓取热榜）"""
    try:
        items = await _fetch_topic_items(limit=30)
        if items:
            _cache["items"] = items
        _cache["fetched_at"] = datetime.utcnow().isoformat()
        _cache["refresh_id"] = int(_cache.get("refresh_id") or 0) + 1
        candidates = _visible_window(_cache["items"], _cache["refresh_id"])
        previous_titles = _cache.get("visible_titles") or []
        current_titles = [item["title"] for item in candidates]
        _cache["visible_titles"] = current_titles
        data = _response(candidates, cached=False, refreshed=True)
        data["changed"] = current_titles != previous_titles
        return data
    except Exception as e:
        logger.warning(f"Refresh failed: {e}")
        candidates = _visible_window(_cache["items"], int(_cache.get("refresh_id") or 1))
        return _response(candidates, cached=True, refreshed=False, error=str(e))
