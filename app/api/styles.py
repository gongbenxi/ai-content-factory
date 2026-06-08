"""Styles API — 风格指纹 CRUD + analyze"""

from __future__ import annotations

import json
import uuid
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.memory_store import STYLES

logger = logging.getLogger(__name__)
router = APIRouter()


class CreateStyleRequest(BaseModel):
    name: str
    description: str = ""


class AnalyzeRequest(BaseModel):
    urls: list[str] = []


@router.get("")
async def list_styles():
    """风格列表"""
    try:
        from sqlalchemy import select
        from app.db.session import get_session
        from app.db.models import Style
        async with get_session() as session:
            result = await session.execute(select(Style).order_by(Style.created_at))
            rows = result.scalars().all()
        return {
            "styles": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "fingerprint": s.fingerprint,
                    "sample_count": s.sample_count,
                    "total_generated": s.total_generated,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in rows
            ]
        }
    except Exception:
        return {"styles": list(STYLES.values()), "_source": "fallback"}


@router.post("")
async def create_style(req: CreateStyleRequest):
    """创建风格"""
    style_id = str(uuid.uuid4())[:8]
    try:
        from app.db.session import get_session
        from app.db.models import Style
        async with get_session() as session:
            style = Style(id=style_id, name=req.name, description=req.description)
            session.add(style)
            await session.commit()
    except Exception:
        STYLES[style_id] = {
            "id": style_id,
            "name": req.name,
            "description": req.description,
            "fingerprint": {},
            "sample_count": 0,
            "total_generated": 0,
        }
    return {"id": style_id, "name": req.name}


@router.get("/{style_id}")
async def get_style(style_id: str):
    """风格详情"""
    try:
        from sqlalchemy import select
        from app.db.session import get_session
        from app.db.models import Style, StyleSample
        async with get_session() as session:
            style = await session.get(Style, style_id)
            if not style:
                return {"error": "not found"}
            samples_q = await session.execute(
                select(StyleSample).where(StyleSample.style_id == style_id).limit(20)
            )
            samples = samples_q.scalars().all()
        return {
            "id": style.id,
            "name": style.name,
            "description": style.description,
            "fingerprint": style.fingerprint,
            "sample_count": style.sample_count,
            "samples": [
                {"id": str(s.id), "title": s.title, "source_url": s.source_url}
                for s in samples
            ],
        }
    except Exception:
        if style_id in STYLES:
            return STYLES[style_id]
        return {"error": "db unavailable", "id": style_id}


@router.post("/{style_id}/analyze")
async def analyze_style(style_id: str, req: AnalyzeRequest):
    """从 URL 抓取文章 → 提取风格指纹 → 入库"""
    from app.tools.scraper import scrape_url
    from app.llm.client import LLMClient

    urls = req.urls or []
    if not urls:
        raise HTTPException(status_code=400, detail="请至少提供 1 个文章 URL")

    style_exists = False
    try:
        from app.db.session import get_session
        from app.db.models import Style
        async with get_session() as session:
            style_exists = bool(await session.get(Style, style_id))
    except Exception:
        style_exists = style_id in STYLES

    if not style_exists:
        raise HTTPException(status_code=404, detail=f"风格不存在：{style_id}")

    # 抓取文章
    articles = []
    scrape_failures = []
    for url in urls[:10]:
        result = await scrape_url(url)
        if result.get("success") and result.get("markdown"):
            articles.append({"url": url, "text": result["markdown"][:3000]})
        else:
            scrape_failures.append({
                "url": url,
                "error": result.get("error") or "未抓取到正文",
            })

    if not articles:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "没有抓取到可分析的文章正文",
                "urls_tried": len(urls),
                "failures": scrape_failures[:5],
            },
        )

    # LLM 提取风格指纹
    llm = LLMClient()
    articles_text = "\n\n---\n\n".join(
        f"[{i+1}] {a['url']}\n{a['text'][:2000]}" for i, a in enumerate(articles)
    )
    messages = [
        {"role": "system", "content": """你是中文写作风格分析专家。给定若干篇文章，提取写作风格指纹。

返回 JSON（不要输出其他内容）:
{
  "syntax_patterns": "短句为主，段落分明...",
  "top_words": ["高频词1", "高频词2", ...],
  "rhetorical_features": "善用比喻和对比...",
  "avg_sentence_len": 15.2,
  "question_ratio": 0.08,
  "emoji_density": 0,
  "second_person_freq": 30,
  "representative_sentences": ["样本句1", "样本句2", "样本句3"]
}"""},
        {"role": "user", "content": f"请分析以下 {len(articles)} 篇文章的写作风格：\n\n{articles_text}"},
    ]

    fingerprint, usage = await llm.chat_json("editor", messages)

    # 确保 fingerprint 是 dict
    if isinstance(fingerprint, str):
        try:
            fingerprint = json.loads(fingerprint)
        except json.JSONDecodeError:
            fingerprint = {"raw": fingerprint}

    # 入库
    try:
        from app.db.session import get_session
        from app.db.models import Style
        async with get_session() as session:
            style = await session.get(Style, style_id)
            if style:
                style.fingerprint = fingerprint
                style.sample_count = len(articles)
                await session.commit()
    except Exception:
        if style_id in STYLES:
            STYLES[style_id]["fingerprint"] = fingerprint
            STYLES[style_id]["sample_count"] = len(articles)

    return {
        "style_id": style_id,
        "status": "done",
        "fingerprint": fingerprint,
        "articles_analyzed": len(articles),
        "scrape_failures": scrape_failures,
    }
