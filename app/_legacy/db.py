"""
数据库层 — SQLite + WAL 模式
================================================================

表结构对齐 PRD §4.9，适配 Phase 1 决策（SQLite 替代 PostgreSQL）：
    runs           — 运行记录（业务侧状态机）
    run_events     — 事件流（SSE 回放用）
    snippets       — 研究素材（可跨 run 复用）
    styles         — 风格指纹
    style_samples  — 风格样本文章

用法:
    from app.db import get_conn, init_db
    init_db()
    conn = get_conn()
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

# ============================================================
# 连接配置
# ============================================================
DB_PATH = os.environ.get("ACF_DB_PATH", os.path.join(os.path.dirname(__file__), "app.db"))


def get_conn() -> sqlite3.Connection:
    """获取 SQLite 连接，启用 WAL 模式和外键约束。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _uuid() -> str:
    return uuid.uuid4().hex


# ============================================================
# 建表 DDL（对齐 PRD §4.9）
# ============================================================
_DDL = """
-- 运行记录（对应 PRD articles 表 + runs 表合并）
CREATE TABLE IF NOT EXISTS runs (
    id              TEXT PRIMARY KEY,
    user_request    TEXT,
    style_id        TEXT NOT NULL DEFAULT '',
    target_platform TEXT NOT NULL DEFAULT 'wechat',
    topic           TEXT,                       -- JSON: {title, angle, hook, ...}
    status          TEXT NOT NULL DEFAULT 'drafting'
                    CHECK(status IN ('drafting','reviewing','needs_human','done','published')),
    current_agent   TEXT,
    draft_md        TEXT,
    final_md        TEXT,
    images          TEXT DEFAULT '[]',           -- JSON array
    review          TEXT,                        -- JSON: {pass, score, issues, summary}
    cost_cents      INTEGER DEFAULT 0,
    error           TEXT,
    started_at      TEXT NOT NULL,
    ended_at        TEXT,
    updated_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS runs_status_idx ON runs(status);
CREATE INDEX IF NOT EXISTS runs_started_at_idx ON runs(started_at DESC);

-- 事件流（SSE 回放用）
CREATE TABLE IF NOT EXISTS run_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id      TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    ts_offset   REAL NOT NULL,       -- 相对 run 开始的秒数
    event_type  TEXT NOT NULL,        -- graph.start / agent.start / tool.call / ...
    data        TEXT NOT NULL DEFAULT '{}',  -- JSON
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS run_events_run_id_idx ON run_events(run_id);

-- 研究素材（可跨 run 复用，避免重复抓取）
CREATE TABLE IF NOT EXISTS snippets (
    id          TEXT PRIMARY KEY,
    source      TEXT,                -- 来源平台
    url         TEXT UNIQUE NOT NULL,
    title       TEXT,
    content     TEXT,
    excerpt     TEXT,
    credibility REAL DEFAULT 0.0,
    angle       TEXT,                -- 背景/数据/案例/观点/趋势
    fetched_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS snippets_fetched_at_idx ON snippets(fetched_at DESC);

-- 风格指纹
CREATE TABLE IF NOT EXISTS styles (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT,
    fingerprint     TEXT NOT NULL DEFAULT '{}',  -- JSON: style_fingerprint 输出
    sample_count    INTEGER DEFAULT 0,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

-- 风格样本文章
CREATE TABLE IF NOT EXISTS style_samples (
    id          TEXT PRIMARY KEY,
    style_id    TEXT NOT NULL REFERENCES styles(id) ON DELETE CASCADE,
    source_url  TEXT,
    text        TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS style_samples_style_id_idx ON style_samples(style_id);

-- Token 用量明细（per-LLM-call）
CREATE TABLE IF NOT EXISTS token_usage (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id          TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    agent           TEXT NOT NULL,
    model           TEXT NOT NULL,
    input_tokens    INTEGER NOT NULL,
    output_tokens   INTEGER NOT NULL,
    cost_cents      INTEGER NOT NULL DEFAULT 0,
    latency_ms      INTEGER,
    created_at      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS token_usage_run_id_idx ON token_usage(run_id);
CREATE INDEX IF NOT EXISTS token_usage_agent_idx ON token_usage(agent, created_at DESC);
"""


def init_db() -> None:
    """启动时自动建表。幂等，可重复调用。"""
    conn = get_conn()
    conn.executescript(_DDL)
    conn.commit()
    conn.close()


# ============================================================
# CRUD 工具函数
# ============================================================

# ---- runs ----

def create_run(
    user_request: str = "",
    style_id: str = "",
    target_platform: str = "wechat",
) -> dict:
    """创建一条运行记录，返回完整 row dict。"""
    now = _now_iso()
    run_id = _uuid()
    conn = get_conn()
    conn.execute(
        """INSERT INTO runs (id, user_request, style_id, target_platform, status, started_at, updated_at)
           VALUES (?, ?, ?, ?, 'drafting', ?, ?)""",
        (run_id, user_request, style_id, target_platform, now, now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    conn.close()
    return dict(row)


def update_run(run_id: str, **fields) -> dict | None:
    """更新 run 的任意字段。fields 的 key 必须是列名。"""
    allowed = {
        "status", "current_agent", "topic", "draft_md", "final_md",
        "images", "review", "cost_cents", "error", "ended_at",
    }
    valid = {k: v for k, v in fields.items() if k in allowed}
    if not valid:
        return get_run(run_id)
    valid["updated_at"] = _now_iso()

    # JSON 字段序列化
    for json_col in ("topic", "images", "review"):
        if json_col in valid and isinstance(valid[json_col], (dict, list)):
            valid[json_col] = json.dumps(valid[json_col], ensure_ascii=False)

    set_clause = ", ".join(f"{k} = ?" for k in valid)
    values = list(valid.values()) + [run_id]
    conn = get_conn()
    conn.execute(f"UPDATE runs SET {set_clause} WHERE id = ?", values)
    conn.commit()
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_run(run_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_runs(
    status: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> list[dict]:
    conn = get_conn()
    if status:
        rows = conn.execute(
            "SELECT * FROM runs WHERE status = ? ORDER BY started_at DESC LIMIT ? OFFSET ?",
            (status, limit, offset),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM runs ORDER BY started_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- run_events ----

def append_event(run_id: str, ts_offset: float, event_type: str, data: dict) -> None:
    """向事件流追加一条事件。"""
    conn = get_conn()
    conn.execute(
        "INSERT INTO run_events (run_id, ts_offset, event_type, data, created_at) VALUES (?, ?, ?, ?, ?)",
        (run_id, ts_offset, event_type, json.dumps(data, ensure_ascii=False), _now_iso()),
    )
    conn.commit()
    conn.close()


def get_events(run_id: str, after_id: int = 0) -> list[dict]:
    """获取 run 的事件流，支持 after_id 增量拉取（SSE 回放）。"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM run_events WHERE run_id = ? AND id > ? ORDER BY id ASC",
        (run_id, after_id),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- snippets ----

def upsert_snippet(snippet: dict) -> None:
    """插入或更新一条素材（按 url 去重）。"""
    conn = get_conn()
    conn.execute(
        """INSERT INTO snippets (id, source, url, title, content, excerpt, credibility, angle, fetched_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(url) DO UPDATE SET
               title = excluded.title,
               content = excluded.content,
               excerpt = excluded.excerpt,
               credibility = excluded.credibility,
               fetched_at = excluded.fetched_at""",
        (
            snippet.get("id", _uuid()),
            snippet.get("source", ""),
            snippet["url"],
            snippet.get("title", ""),
            snippet.get("content", ""),
            snippet.get("excerpt", ""),
            snippet.get("credibility", 0.0),
            snippet.get("angle", ""),
            _now_iso(),
        ),
    )
    conn.commit()
    conn.close()


def get_snippet_by_url(url: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM snippets WHERE url = ?", (url,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_recent_snippets(hours: int = 24, limit: int = 100) -> list[dict]:
    """获取最近 N 小时内的素材（L1 新鲜素材检索）。"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM snippets ORDER BY fetched_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ---- styles ----

def create_style(name: str, description: str = "", fingerprint: dict | None = None) -> dict:
    now = _now_iso()
    style_id = _uuid()
    conn = get_conn()
    conn.execute(
        """INSERT INTO styles (id, name, description, fingerprint, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (style_id, name, description, json.dumps(fingerprint or {}, ensure_ascii=False), now, now),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM styles WHERE id = ?", (style_id,)).fetchone()
    conn.close()
    return dict(row)


def get_style(style_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute("SELECT * FROM styles WHERE id = ?", (style_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def list_styles() -> list[dict]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM styles ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_style(style_id: str, **fields) -> dict | None:
    allowed = {"name", "description", "fingerprint", "sample_count"}
    valid = {k: v for k, v in fields.items() if k in allowed}
    if not valid:
        return get_style(style_id)
    valid["updated_at"] = _now_iso()
    if "fingerprint" in valid and isinstance(valid["fingerprint"], (dict, list)):
        valid["fingerprint"] = json.dumps(valid["fingerprint"], ensure_ascii=False)

    set_clause = ", ".join(f"{k} = ?" for k in valid)
    values = list(valid.values()) + [style_id]
    conn = get_conn()
    conn.execute(f"UPDATE styles SET {set_clause} WHERE id = ?", values)
    conn.commit()
    row = conn.execute("SELECT * FROM styles WHERE id = ?", (style_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_style(style_id: str) -> bool:
    conn = get_conn()
    cursor = conn.execute("DELETE FROM styles WHERE id = ?", (style_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


# ---- style_samples ----

def add_style_sample(style_id: str, text: str, source_url: str = "") -> dict:
    sample_id = _uuid()
    conn = get_conn()
    conn.execute(
        "INSERT INTO style_samples (id, style_id, source_url, text, created_at) VALUES (?, ?, ?, ?, ?)",
        (sample_id, style_id, source_url, text, _now_iso()),
    )
    # 更新 sample_count
    conn.execute(
        "UPDATE styles SET sample_count = sample_count + 1, updated_at = ? WHERE id = ?",
        (_now_iso(), style_id),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM style_samples WHERE id = ?", (sample_id,)).fetchone()
    conn.close()
    return dict(row)


def get_style_samples(style_id: str) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM style_samples WHERE style_id = ? ORDER BY created_at DESC",
        (style_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_style_sample(sample_id: str) -> bool:
    conn = get_conn()
    row = conn.execute("SELECT style_id FROM style_samples WHERE id = ?", (sample_id,)).fetchone()
    if not row:
        conn.close()
        return False
    style_id = row["style_id"]
    conn.execute("DELETE FROM style_samples WHERE id = ?", (sample_id,))
    conn.execute(
        "UPDATE styles SET sample_count = MAX(sample_count - 1, 0), updated_at = ? WHERE id = ?",
        (_now_iso(), style_id),
    )
    conn.commit()
    conn.close()
    return True


# ---- token_usage ----

def append_token_usage(
    run_id: str,
    agent: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cost_cents: int = 0,
    latency_ms: int | None = None,
) -> None:
    """记录一次 LLM 调用的 token 用量。"""
    conn = get_conn()
    conn.execute(
        """INSERT INTO token_usage (run_id, agent, model, input_tokens, output_tokens, cost_cents, latency_ms, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_id, agent, model, input_tokens, output_tokens, cost_cents, latency_ms, _now_iso()),
    )
    conn.commit()
    conn.close()


def get_token_usage_by_run(run_id: str) -> list[dict]:
    """获取某次 run 的所有 token 用量记录。"""
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM token_usage WHERE run_id = ? ORDER BY id ASC",
        (run_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_token_usage_summary(run_id: str) -> dict:
    """按 agent 聚合某次 run 的 token 用量。"""
    conn = get_conn()
    rows = conn.execute(
        """SELECT agent, SUM(input_tokens) as input_tokens, SUM(output_tokens) as output_tokens,
                  SUM(cost_cents) as cost_cents, COUNT(*) as call_count
           FROM token_usage WHERE run_id = ? GROUP BY agent""",
        (run_id,),
    ).fetchall()
    conn.close()
    return {r["agent"]: dict(r) for r in rows}


# ---- dashboard stats ----

def get_dashboard_stats() -> dict:
    """聚合仪表盘统计数据（对应 PRD §4.10 Dashboard 页面）。"""
    conn = get_conn()
    total = conn.execute("SELECT COUNT(*) as c FROM runs").fetchone()["c"]
    done = conn.execute("SELECT COUNT(*) as c FROM runs WHERE status = 'done'").fetchone()["c"]
    drafting = conn.execute("SELECT COUNT(*) as c FROM runs WHERE status = 'drafting'").fetchone()["c"]
    needs_human = conn.execute("SELECT COUNT(*) as c FROM runs WHERE status = 'needs_human'").fetchone()["c"]
    total_cost = conn.execute("SELECT COALESCE(SUM(cost_cents), 0) as s FROM runs").fetchone()["s"]
    snippet_count = conn.execute("SELECT COUNT(*) as c FROM snippets").fetchone()["c"]
    style_count = conn.execute("SELECT COUNT(*) as c FROM styles").fetchone()["c"]
    conn.close()
    return {
        "total_runs": total,
        "done_runs": done,
        "drafting_runs": drafting,
        "needs_human_runs": needs_human,
        "total_cost_cents": total_cost,
        "snippet_count": snippet_count,
        "style_count": style_count,
    }
