"""
路由 — /api/settings（对应 PRD §6e / §4.10 Settings 页面）
================================================================
"""

from __future__ import annotations

import os

from fastapi import APIRouter

from app.models import SettingsResponse, SettingsUpdateRequest
from app.db import DB_PATH

router = APIRouter(prefix="/api/settings", tags=["settings"])

# 运行时配置存储（内存级，重启丢失）
_runtime_config: dict = {}


@router.get("", response_model=SettingsResponse)
async def api_get_settings():
    """读取系统配置。"""
    return SettingsResponse(
        base_url=_runtime_config.get("base_url", os.environ.get("MIMO_BASE_URL", "https://token-plan-cn.xiaomimimo.com/v1")),
        model=_runtime_config.get("model", os.environ.get("MIMO_MODEL", "mimo-v2.5-pro")),
        model_fast=_runtime_config.get("model_fast", os.environ.get("MIMO_MODEL_FAST", "mimo-v2.5")),
        db_path=DB_PATH,
        max_revise_rounds=_runtime_config.get("max_revise_rounds", 2),
    )


@router.put("", response_model=SettingsResponse)
async def api_update_settings(req: SettingsUpdateRequest):
    """更新系统配置。"""
    if req.base_url is not None:
        _runtime_config["base_url"] = req.base_url
    if req.model is not None:
        _runtime_config["model"] = req.model
    if req.model_fast is not None:
        _runtime_config["model_fast"] = req.model_fast
    if req.max_revise_rounds is not None:
        _runtime_config["max_revise_rounds"] = req.max_revise_rounds
    return await api_get_settings()
