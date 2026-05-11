"""Topics API — 选题候选"""

from __future__ import annotations

import logging
from fastapi import APIRouter

from app.services.memory_store import RUNS

logger = logging.getLogger(__name__)
router = APIRouter()

# 缓存最近一次刷新结果
_cache: dict = {"items": [], "fetched_at": None}


@router.get("/candidates")
async def get_candidates():
    """今日候选选题"""
    if _cache["items"]:
        return {"candidates": _cache["items"][:5]}
    try:
        from app.tools.hotnews import fetch_hotnews_unified
        items = await fetch_hotnews_unified(limit=10, sources=["baidu"])
        _cache["items"] = items
        return {"candidates": items[:5]}
    except Exception as e:
        return {"candidates": [], "error": str(e)}


@router.post("/refresh")
async def refresh_candidates():
    """强制刷新选题（重新抓取热榜）"""
    try:
        from datetime import datetime
        from app.tools.hotnews import fetch_hotnews_unified
        items = await fetch_hotnews_unified(limit=10, sources=["baidu"])
        _cache["items"] = items
        _cache["fetched_at"] = datetime.utcnow().isoformat()
        return {"refreshed": True, "count": len(items), "candidates": items[:5]}
    except Exception as e:
        logger.warning(f"Refresh failed: {e}")
        return {"refreshed": False, "error": str(e), "count": 0}
