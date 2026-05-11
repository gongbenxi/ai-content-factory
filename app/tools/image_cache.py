"""图像缓存 — SHA256 prompt_hash + image_cache 表"""

from __future__ import annotations

import hashlib
import logging

logger = logging.getLogger(__name__)


def calc_prompt_hash(enhanced_prompt: str, size: str, model: str) -> str:
    """计算图像生成 prompt 的 hash"""
    raw = f"{enhanced_prompt}|{size}|{model}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def get_cached_image(prompt_hash: str) -> dict | None:
    """查询缓存，命中则返回 {url, local_path, model, size}，并自增 hit_count"""
    try:
        from app.db.session import get_session
        from sqlalchemy import text

        async with get_session() as session:
            result = await session.execute(
                text("""
                    SELECT url, local_path, model, size
                    FROM image_cache
                    WHERE prompt_hash = :prompt_hash
                """),
                {"prompt_hash": prompt_hash},
            )
            row = result.mappings().first()
            if not row:
                return None

            # 自增 hit_count
            await session.execute(
                text("""
                    UPDATE image_cache
                    SET hit_count = hit_count + 1
                    WHERE prompt_hash = :prompt_hash
                """),
                {"prompt_hash": prompt_hash},
            )
            await session.commit()

            return {
                "url": row["url"],
                "local_path": row["local_path"],
                "model": row["model"],
                "size": row["size"],
                "cached": True,
            }
    except Exception as e:
        logger.debug(f"Image cache read skipped: {e}")
        return None


async def save_to_cache(prompt_hash: str, url: str, local_path: str, model: str, size: str):
    """保存生成结果到缓存"""
    try:
        from app.db.session import get_session
        from sqlalchemy import text

        async with get_session() as session:
            await session.execute(
                text("""
                INSERT INTO image_cache (prompt_hash, url, local_path, model, size)
                VALUES (:prompt_hash, :url, :local_path, :model, :size)
                ON CONFLICT (prompt_hash) DO NOTHING
                """),
                {
                    "prompt_hash": prompt_hash,
                    "url": url,
                    "local_path": local_path,
                    "model": model,
                    "size": size,
                },
            )
            await session.commit()
    except Exception as e:
        logger.debug(f"Image cache write skipped: {e}")
