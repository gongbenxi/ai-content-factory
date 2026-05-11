"""
路由 — /api/styles/*（对应 PRD §6c / §4.10 风格管理）
================================================================
"""

from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from app.models import (
    StyleCreateRequest, StyleUpdateRequest, StyleSampleCreate,
    StyleResponse, StyleListResponse,
)
from app.db import (
    create_style, get_style, list_styles, update_style, delete_style,
    add_style_sample, get_style_samples, delete_style_sample,
)

router = APIRouter(prefix="/api/styles", tags=["styles"])


@router.get("", response_model=StyleListResponse)
async def api_list_styles():
    """风格列表。"""
    styles = list_styles()
    return StyleListResponse(items=[_to_response(s) for s in styles])


@router.get("/{style_id}", response_model=StyleResponse)
async def api_get_style(style_id: str):
    """风格详情。"""
    style = get_style(style_id)
    if not style:
        raise HTTPException(404, f"Style {style_id} not found")
    return _to_response(style)


@router.post("", response_model=StyleResponse)
async def api_create_style(req: StyleCreateRequest):
    """新建风格。"""
    style = create_style(
        name=req.name,
        description=req.description,
        fingerprint=req.fingerprint,
    )
    return _to_response(style)


@router.put("/{style_id}", response_model=StyleResponse)
async def api_update_style(style_id: str, req: StyleUpdateRequest):
    """更新风格。"""
    style = get_style(style_id)
    if not style:
        raise HTTPException(404, f"Style {style_id} not found")
    fields = {}
    if req.name is not None:
        fields["name"] = req.name
    if req.description is not None:
        fields["description"] = req.description
    if req.fingerprint is not None:
        fields["fingerprint"] = req.fingerprint
    updated = update_style(style_id, **fields)
    return _to_response(updated)


@router.delete("/{style_id}")
async def api_delete_style(style_id: str):
    """删除风格。"""
    if not delete_style(style_id):
        raise HTTPException(404, f"Style {style_id} not found")
    return {"status": "deleted", "style_id": style_id}


@router.post("/{style_id}/samples")
async def api_add_sample(style_id: str, req: StyleSampleCreate):
    """上传范文（对应 PRD M5）。"""
    style = get_style(style_id)
    if not style:
        raise HTTPException(404, f"Style {style_id} not found")
    sample = add_style_sample(
        style_id=style_id,
        text=req.text,
        source_url=req.source_url,
    )
    return {"status": "added", "sample_id": sample["id"]}


@router.get("/{style_id}/samples")
async def api_get_samples(style_id: str):
    """获取风格的范文列表。"""
    style = get_style(style_id)
    if not style:
        raise HTTPException(404, f"Style {style_id} not found")
    samples = get_style_samples(style_id)
    return samples


@router.delete("/{style_id}/samples/{sample_id}")
async def api_delete_sample(style_id: str, sample_id: str):
    """删除范文。"""
    if not delete_style_sample(sample_id):
        raise HTTPException(404, f"Sample {sample_id} not found")
    return {"status": "deleted", "sample_id": sample_id}


@router.post("/{style_id}/analyze")
async def api_analyze_style(style_id: str):
    """触发指纹分析（对应 PRD M5）。"""
    style = get_style(style_id)
    if not style:
        raise HTTPException(404, f"Style {style_id} not found")
    samples = get_style_samples(style_id)
    if len(samples) < 5:
        raise HTTPException(
            400,
            f"风格样本不足（当前 {len(samples)} 篇，最低 5 篇）。请先上传更多范文。",
        )
    # TODO: 调用 style_fingerprint skill 分析
    return {
        "status": "analyzing",
        "style_id": style_id,
        "sample_count": len(samples),
        "message": "指纹分析已触发（Phase 1 预留接口）",
    }


def _to_response(style: dict) -> StyleResponse:
    return StyleResponse(
        id=style["id"],
        name=style["name"],
        description=style.get("description", ""),
        fingerprint=json.loads(style["fingerprint"]) if style.get("fingerprint") else {},
        sample_count=style.get("sample_count", 0),
        created_at=style.get("created_at", ""),
        updated_at=style.get("updated_at", ""),
    )
