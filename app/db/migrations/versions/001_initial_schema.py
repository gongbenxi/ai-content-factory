"""initial schema — 7 tables + pgvector

Revision ID: 001
Create Date: 2026-05-11
"""

from alembic import op

# revision identifiers
revision = "001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA_SQL = """
-- pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 风格指纹主表
CREATE TABLE IF NOT EXISTS styles (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    fingerprint     JSONB DEFAULT '{}',
    sample_count    INT DEFAULT 0,
    total_generated INT DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 运行 / 文章主表
CREATE TABLE IF NOT EXISTS runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_request    TEXT,
    style_id        TEXT REFERENCES styles(id),
    target_platform TEXT NOT NULL,
    config          JSONB DEFAULT '{}',
    topic           JSONB,
    outline         JSONB,
    final_outline   JSONB,
    draft_md        TEXT,
    final_md        TEXT,
    images          JSONB DEFAULT '[]',
    review          JSONB,
    revise_count    INT DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'drafting'
           CHECK (status IN ('drafting', 'reviewing', 'needs_human', 'done', 'published', 'failed', 'paused', 'aborted')),
    current_agent   TEXT,
    error           TEXT,
    cost_cents      INT DEFAULT 0,
    total_tokens    INT DEFAULT 0,
    usage_by_agent  JSONB DEFAULT '{}',
    embedding       VECTOR(1024),
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS runs_status_idx     ON runs(status);
CREATE INDEX IF NOT EXISTS runs_started_at_idx ON runs(started_at DESC);
CREATE INDEX IF NOT EXISTS runs_embedding_idx  ON runs USING ivfflat (embedding vector_cosine_ops);

-- 事件流
CREATE TABLE IF NOT EXISTS run_events (
    id          BIGSERIAL PRIMARY KEY,
    run_id      UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    ts_offset   REAL NOT NULL,
    event_type  TEXT NOT NULL,
    data        JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS run_events_run_idx  ON run_events(run_id, id);
CREATE INDEX IF NOT EXISTS run_events_type_idx ON run_events(event_type, created_at DESC);

-- 研究素材
CREATE TABLE IF NOT EXISTS snippets (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source      TEXT,
    url         TEXT UNIQUE NOT NULL,
    title       TEXT,
    content     TEXT,
    excerpt     TEXT,
    credibility FLOAT,
    angle       TEXT,
    embedding   VECTOR(1024),
    fetched_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS snippets_embedding_idx  ON snippets USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS snippets_fetched_at_idx ON snippets(fetched_at DESC);

-- 风格样本范文
CREATE TABLE IF NOT EXISTS style_samples (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    style_id    TEXT NOT NULL REFERENCES styles(id) ON DELETE CASCADE,
    source_url  TEXT,
    title       TEXT,
    text        TEXT NOT NULL,
    embedding   VECTOR(1024),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS style_samples_style_idx ON style_samples(style_id);

-- 图片生成缓存
CREATE TABLE IF NOT EXISTS image_cache (
    prompt_hash TEXT PRIMARY KEY,
    url         TEXT NOT NULL,
    local_path  TEXT,
    model       TEXT NOT NULL,
    size        TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    hit_count   INT DEFAULT 0
);

-- Token 消耗明细
CREATE TABLE IF NOT EXISTS token_usage (
    id                BIGSERIAL PRIMARY KEY,
    run_id            UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    agent             TEXT NOT NULL,
    provider          TEXT NOT NULL,
    model             TEXT NOT NULL,
    input_tokens      INT NOT NULL,
    output_tokens     INT NOT NULL,
    cache_read_tokens INT DEFAULT 0,
    cost_cents        INT NOT NULL,
    latency_ms        INT,
    created_at        TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS token_usage_run_idx   ON token_usage(run_id);
CREATE INDEX IF NOT EXISTS token_usage_agent_idx ON token_usage(agent, created_at DESC);
"""

DROP_SQL = """
DROP TABLE IF EXISTS token_usage;
DROP TABLE IF EXISTS image_cache;
DROP TABLE IF EXISTS style_samples;
DROP TABLE IF EXISTS snippets;
DROP TABLE IF EXISTS run_events;
DROP TABLE IF EXISTS runs;
DROP TABLE IF EXISTS styles;
"""


def upgrade() -> None:
    op.execute(SCHEMA_SQL)


def downgrade() -> None:
    op.execute(DROP_SQL)
