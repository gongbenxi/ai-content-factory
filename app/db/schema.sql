-- ============================================================
-- AI Content Factory — DB Schema (PostgreSQL 16 + pgvector)
-- ============================================================

-- 风格指纹主表
CREATE TABLE styles (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    description     TEXT DEFAULT '',
    fingerprint     JSONB DEFAULT '{}',
    sample_count    INT DEFAULT 0,
    total_generated INT DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- 运行 / 文章主表（合并模型：一个 run 即一篇文章）
CREATE TABLE runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 输入
    user_request    TEXT,
    style_id        TEXT REFERENCES styles(id),
    target_platform TEXT NOT NULL,
    config          JSONB DEFAULT '{}',

    -- 中间产物
    topic           JSONB,
    outline         JSONB,
    final_outline   JSONB,
    draft_md        TEXT,
    final_md        TEXT,
    images          JSONB DEFAULT '[]',
    review          JSONB,
    revise_count    INT DEFAULT 0,

    -- 状态机
    status TEXT NOT NULL DEFAULT 'drafting'
           CHECK (status IN ('drafting', 'reviewing', 'needs_human', 'done', 'published', 'failed', 'paused', 'aborted')),
    current_agent   TEXT,
    error           TEXT,

    -- 计量
    cost_cents      INT DEFAULT 0,
    total_tokens    INT DEFAULT 0,
    usage_by_agent  JSONB DEFAULT '{}',

    -- 检索用
    embedding       VECTOR(1024),

    -- 时间戳
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    ended_at        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX runs_status_idx     ON runs(status);
CREATE INDEX runs_started_at_idx ON runs(started_at DESC);
CREATE INDEX runs_embedding_idx  ON runs USING ivfflat (embedding vector_cosine_ops);

-- 事件流（SSE 实时推送 + 历史回放）
CREATE TABLE run_events (
    id          BIGSERIAL PRIMARY KEY,
    run_id      UUID NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
    ts_offset   REAL NOT NULL,
    event_type  TEXT NOT NULL,
    data        JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX run_events_run_idx  ON run_events(run_id, id);
CREATE INDEX run_events_type_idx ON run_events(event_type, created_at DESC);

-- 研究素材（可跨 run 复用）
CREATE TABLE snippets (
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
CREATE INDEX snippets_embedding_idx  ON snippets USING ivfflat (embedding vector_cosine_ops);
CREATE INDEX snippets_fetched_at_idx ON snippets(fetched_at DESC);

-- 风格样本范文
CREATE TABLE style_samples (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    style_id    TEXT NOT NULL REFERENCES styles(id) ON DELETE CASCADE,
    source_url  TEXT,
    title       TEXT,
    text        TEXT NOT NULL,
    embedding   VECTOR(1024),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX style_samples_style_idx ON style_samples(style_id);

-- 图片生成缓存
CREATE TABLE image_cache (
    prompt_hash TEXT PRIMARY KEY,
    url         TEXT NOT NULL,
    local_path  TEXT,
    model       TEXT NOT NULL,
    size        TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    hit_count   INT DEFAULT 0
);

-- Token 消耗明细
CREATE TABLE token_usage (
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
CREATE INDEX token_usage_run_idx   ON token_usage(run_id);
CREATE INDEX token_usage_agent_idx ON token_usage(agent, created_at DESC);
