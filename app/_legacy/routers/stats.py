"""
路由 — /api/stats/*（对应 PRD §6d / §4.10 Dashboard）
================================================================
"""

from __future__ import annotations

from fastapi import APIRouter

from app.models import DashboardStats
from app.db import get_dashboard_stats

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/dashboard", response_model=DashboardStats)
async def api_dashboard_stats():
    """仪表盘聚合数据（对应 PRD §4.10 Dashboard 页面）。"""
    return get_dashboard_stats()
