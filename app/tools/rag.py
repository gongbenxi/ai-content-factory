"""RAG 双层检索 — BGE-M3 embed + pgvector

L1: snippets 表（24h 新鲜素材复用）
L2: runs 表（90d 历史避重）
"""

from __future__ import annotations

import os


async def embed_text(text: str) -> list[float]:
    """调用 BGE-M3 生成 embedding（1024 维）。

    Phase 1 可用 mock 返回随机向量。
    """
    embedding_model = os.getenv("EMBEDDING_MODEL", "mock")
    if embedding_model == "mock":
        import random
        random.seed(hash(text) % 2**32)
        return [random.uniform(-1, 1) for _ in range(1024)]

    # TODO: 接入 BGE-M3 本地部署或 API
    raise NotImplementedError("BGE-M3 embedding 尚未接入")


async def vector_search_snippets(query: str, k: int = 5, hours: int = 24) -> list[dict]:
    """L1 检索：在 snippets 表中搜索最近 N 小时的相关素材"""
    from app.db.session import get_session

    emb = await embed_text(query)
    emb_str = str(emb)

    async with get_session() as session:
        result = await session.execute(
            """
            SELECT id, source, url, title, excerpt, credibility, angle,
                   1 - (embedding <=> $1::vector) AS sim
            FROM snippets
            WHERE fetched_at > NOW() - INTERVAL '$2 hours'
              AND embedding IS NOT NULL
            ORDER BY embedding <=> $1::vector
            LIMIT $3
            """,
            emb_str, hours, k,
        )
        rows = result.fetchall()

    return [
        {
            "id": str(r[0]),
            "source": r[1],
            "url": r[2],
            "title": r[3],
            "excerpt": r[4],
            "credibility": r[5],
            "angle": r[6],
            "similarity": r[7],
        }
        for r in rows
    ]


async def vector_search_history(query: str, k: int = 5, days: int = 90) -> list[dict]:
    """L2 检索：在 runs 表中搜索最近 N 天的已完成文章，避免重复"""
    from app.db.session import get_session

    emb = await embed_text(query)
    emb_str = str(emb)

    async with get_session() as session:
        result = await session.execute(
            """
            SELECT id, topic, final_md, 1 - (embedding <=> $1::vector) AS sim
            FROM runs
            WHERE status IN ('done', 'published')
              AND created_at > NOW() - INTERVAL '$2 days'
              AND embedding IS NOT NULL
            ORDER BY embedding <=> $1::vector
            LIMIT $3
            """,
            emb_str, days, k,
        )
        rows = result.fetchall()

    return [
        {
            "id": str(r[0]),
            "topic": r[1],
            "similarity": r[3],
        }
        for r in rows
    ]
