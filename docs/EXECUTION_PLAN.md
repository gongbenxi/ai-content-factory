# AI Content Factory — 执行计划

> 直接按 PRD 功能模块分步实施。每步交付可运行的代码，有明确验收标准。

---

## Step 1 — 项目骨架 + 基础设施

对应 PRD: §6.3 文件结构 / §6.5 环境变量 / §5.1 性能约束

### 1.1 归档旧代码

```bash
mkdir -p app/_legacy
mv app/agents/graph.py app/_legacy/graph_asyncio.py
mv app/services/runner.py app/_legacy/runner_asyncio.py
```

### 1.2 创建最终目录结构

```
app/
├── main.py
├── config.py                    # Pydantic Settings（§6.1 models.yaml + 环境变量）
├── agents/
│   ├── graph.py                 # LangGraph StateGraph
│   ├── topic.py
│   ├── planner.py
│   ├── researcher.py
│   ├── editor.py
│   ├── writer.py
│   ├── illustrator.py
│   ├── reviewer.py
│   └── reviser.py
├── tools/
│   ├── hotnews.py               # ✅ 已完成
│   ├── rss.py
│   ├── style.py
│   ├── search.py
│   ├── scraper.py
│   ├── rag.py
│   ├── safety.py
│   └── image.py
├── api/
│   ├── runs.py
│   ├── styles.py
│   ├── topics.py
│   ├── stats.py
│   └── settings.py
├── llm/
│   ├── client.py                # 多 Provider 切换（§6.1）
│   ├── budget.py                # 预算熔断（§4.11）
│   └── prompts/                 # Agent prompt 文件（§7）
├── db/
│   ├── schema.sql
│   └── models.py
├── observability/
│   └── langfuse.py
└── workers/
    └── runner.py                # LangGraph driver
config/
└── models.yaml                  # 模型分级配置（§6.1）
frontend/                        # React
docker-compose.yml               # postgres + redis + langfuse
```

### 1.3 `config/models.yaml`

照搬 PRD §6.1 多 Provider 切换机制：

```yaml
providers:
  xiaomi:
    base_url: "https://token-plan-cn.xiaomimimo.com/v1"
    api_key_env: "MIMO_API_KEY"
    models:
      fast: "MiMo-V2.5"
      balanced: "MiMo-V2.5-Pro"
  deepseek:
    base_url: "https://api.deepseek.com/v1"
    api_key_env: "DEEPSEEK_API_KEY"
    models:
      fast: "deepseek-chat"
      balanced: "deepseek-chat"
  openai:
    base_url: "https://api.openai.com/v1"
    api_key_env: "OPENAI_API_KEY"
    models:
      fast: "gpt-4o-mini"
      balanced: "gpt-4o"

defaults:
  active_provider: xiaomi

agents:
  topic:      { provider: xiaomi, tier: fast }
  researcher: { provider: xiaomi, tier: fast }
  planner:    { provider: xiaomi, tier: balanced }
  editor:     { provider: xiaomi, tier: balanced }
  writer:     { provider: xiaomi, tier: balanced }
  reviewer:   { provider: xiaomi, tier: balanced }
  reviser:    { provider: xiaomi, tier: balanced }

budget:
  max_tokens_per_run: 200000
  warn_at_percent: 80
  fallback_tier: fast
```

### 1.4 `app/config.py`

Pydantic Settings 读 `models.yaml` + `.env`。硬约束常量（§5.1）：

| 约束 | 值 |
|---|---|
| 单次 LLM 超时 | 60s |
| LLM 重试 | 3 次指数退避 |
| 单 run 总超时 | 12min |
| 并发 run 上限 | 5 |
| SSE 心跳 | 15s |

### 1.5 `docker-compose.yml`

PostgreSQL 16 + pgvector / Redis / Langfuse。

### 1.6 依赖安装

```bash
pip install langgraph langchain-core \
            fastapi uvicorn openai \
            psycopg[binary] redis celery \
            tavily-python httpx crawl4ai \
            pyecharts pillow playwright \
            feedparser tenacity langfuse \
            pydantic-settings pyyaml
playwright install chromium
```

### 1.7 前端初始化

```bash
npx create-next-app@latest frontend --ts --tailwind --app --src-dir
cd frontend
npm install @shadcn/ui @tiptap/react zustand
```

### 验收

- [ ] `docker compose up` 启动 PG + Redis + Langfuse
- [ ] `uvicorn app.main:app` 启动成功，`/docs` 可访问
- [ ] `cd frontend && npm run dev` 启动成功
- [ ] `config/models.yaml` 能被 `app/config.py` 正确读取

---

## Step 2 — 数据库 Schema

对应 PRD: §4.12 数据层

### 2.1 `app/db/schema.sql`

完整 7 表（直接照搬 PRD §4.12.2）：

```sql
-- runs（合并模型：1 run = 1 article）
CREATE TABLE runs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_request    TEXT NOT NULL,
    style_id        UUID REFERENCES styles(id),
    target_platform TEXT NOT NULL DEFAULT 'wechat',
    topic           JSONB,
    outline         JSONB,
    draft_md        TEXT,
    final_md        TEXT,
    images          JSONB DEFAULT '[]',
    review          JSONB,
    status          TEXT NOT NULL DEFAULT 'drafting',
    current_agent   TEXT,
    cost_cents      INTEGER DEFAULT 0,
    error           TEXT,
    config          JSONB DEFAULT '{}',
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at        TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- run_events（全链路事件流）
CREATE TABLE run_events (
    id          BIGSERIAL PRIMARY KEY,
    run_id      UUID NOT NULL REFERENCES runs(id),
    ts_offset   REAL NOT NULL,
    event_type  TEXT NOT NULL,
    data        JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- snippets（研究素材）
CREATE TABLE snippets (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      UUID NOT NULL REFERENCES runs(id),
    query       TEXT NOT NULL,
    title       TEXT,
    url         TEXT,
    content     TEXT NOT NULL,
    credibility REAL DEFAULT 0.5,
    embedding   vector(1024),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- styles（风格指纹）
CREATE TABLE styles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    description TEXT,
    fingerprint JSONB,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- style_samples（范文）
CREATE TABLE style_samples (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    style_id    UUID NOT NULL REFERENCES styles(id) ON DELETE CASCADE,
    content     TEXT NOT NULL,
    source_url  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- image_cache（图片缓存）
CREATE TABLE image_cache (
    prompt_hash TEXT PRIMARY KEY,
    prompt      TEXT NOT NULL,
    model       TEXT NOT NULL,
    size        TEXT NOT NULL DEFAULT '1024x1024',
    url         TEXT NOT NULL,
    local_path  TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    hit_count   INTEGER NOT NULL DEFAULT 0
);

-- token_usage（Token 明细）
CREATE TABLE token_usage (
    id              BIGSERIAL PRIMARY KEY,
    run_id          UUID NOT NULL REFERENCES runs(id),
    agent           TEXT NOT NULL,
    provider        TEXT NOT NULL,
    model           TEXT NOT NULL,
    prompt_tokens   INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    cache_read_tokens INTEGER DEFAULT 0,
    cost_cents      REAL NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 2.2 索引 + pgvector

```sql
CREATE INDEX idx_runs_status ON runs(status);
CREATE INDEX idx_run_events_run_id ON run_events(run_id, id);
CREATE INDEX idx_snippets_run ON snippets(run_id);
CREATE INDEX idx_token_usage_run ON token_usage(run_id);
CREATE INDEX idx_snippets_embedding ON snippets USING ivfflat (embedding vector_cosine_ops);
```

### 2.3 Alembic 初始化

```bash
alembic init app/db/migrations
alembic revision --autogenerate -m "initial schema"
alembic upgrade head
```

### 验收

- [ ] `alembic upgrade head` → 7 表全部创建
- [ ] pgvector 扩展已启用，embedding 列可写入
- [ ] `psql` 手动 INSERT 一条 run → SELECT 正常

---

## Step 3 — LLM 抽象层 + 多 Provider 切换

对应 PRD: §6.1 多 Provider / §4.11 Token 监控

### 3.1 `app/llm/client.py`

```python
class LLMClient:
    """读 config/models.yaml，按 agent 名路由到对应 provider + model。"""
    async def chat(self, agent: str, messages, **kwargs) -> ChatCompletion
    async def chat_json(self, agent: str, messages, schema) -> dict
    async def stream(self, agent: str, messages) -> AsyncGenerator
```

- 内部用 `AsyncOpenAI(base_url=..., api_key=...)`
- 自动附加 `tenacity.retry`（3 次指数退避，60s 超时）
- 每次调用后自动写 `token_usage` 表

### 3.2 `app/llm/budget.py`

PRD §4.11 预算熔断：
- 调用前查 `SUM(token_usage) WHERE run_id=?`
- ≥80%：把当前 agent 的 tier 降级为 `fast`
- ≥100%：抛 `BudgetExceeded`

### 3.3 `app/llm/prompts/*.txt`

PRD §7 的 3 个 prompt 模板 + 其余 agent 的 prompt 占位。

### 3.4 Langfuse 集成 `app/observability/langfuse.py`

PRD §5.5：每次 LLM 调用自动 trace（prompt / completion / tokens / latency / cost）。

### 验收

- [ ] `LLMClient.chat("topic", [...])` → 返回 MiMo 响应
- [ ] 切 `models.yaml` 的 `active_provider` → 走 DeepSeek（或报 key 缺失）
- [ ] `token_usage` 表有记录
- [ ] Langfuse dashboard 能看到 trace
- [ ] 设 `max_tokens_per_run: 100` → 触发 `BudgetExceeded`

---

## Step 4 — 工具层

对应 PRD: §4.2 选题（热搜）/ §4.4 研究（搜索+抓取）/ §4.13 Skills_Repo / §4.7 配图

### 4.1 `app/tools/hotnews.py` ✅ 已完成

### 4.2 `app/tools/rss.py`

从 `skills/rss_fetcher/scripts/fetch.py` 提取 RSS 解析逻辑，暴露 `async fetch_rss(limit, categories)`。

### 4.3 `app/tools/style.py`

从 `skills/style_fingerprint/style_fingerprint.py` 提取 `SimpleChineseTokenizer` + `StyleFingerprint`，暴露 `analyze_style(text) -> dict`。

### 4.4 `app/tools/search.py`

Tavily API 封装（PRD §6.1 Web 搜索）：`async web_search(q, n=5) -> list[dict]`。

### 4.5 `app/tools/scraper.py`

Crawl4AI 封装（PRD §6.1 浏览器抓取）：`async scrape(url) -> {title, content_md, word_count}`。

### 4.6 `app/tools/rag.py`

PRD §4.12.3：BGE-M3 embedding + pgvector 存取 + 相似度检索。

### 4.7 `app/tools/safety.py`

PRD §5.4 / §6.1：自建敏感词库检查。

### 4.8 `app/tools/image.py`

PRD §4.7 五路径混合：

| 子模块 | 实现 |
|---|---|
| `generate_cover(prompt)` | 硅基流动 Kolors（n=2 候选） |
| `generate_illustration(prompt)` | 硅基流动 FLUX.1-schnell |
| `generate_chart(data, chart_type)` | pyecharts → Playwright 截图 |
| `generate_card(title, subtitle)` | Pillow 渲染 |
| `generate_infographic(data)` | HTML 模板 + Playwright 截图 |
| `enhance_prompt(desc, context)` | LLM 中文→英文增强 |
| `check_cache(prompt_hash)` | image_cache 表查询 |

Provider 备份链：硅基流动 → 火山即梦 → Coze Seedream。

### 验收

- [ ] 每个工具有独立 `tests/tools/test_*.py`
- [ ] `fetch_hotnews(20)` + `fetch_rss(10)` → 聚合 30 条
- [ ] `analyze_style(text)` → 风格指纹 JSON
- [ ] `web_search("AI")` → 5 条结果
- [ ] `scrape(url)` → markdown 正文
- [ ] `generate_cover(prompt)` → 返回图片 URL
- [ ] `generate_chart({...})` → 生成 PNG

---

## Step 5 — LangGraph 状态机 + 7 个 Agent 节点

对应 PRD: §4.10 LangGraph 状态机 / §4.1–4.9 各 Agent

### 5.1 `app/agents/graph.py` — 状态定义 + 图装配

PRD §4.10 的完整状态机：

```python
class ContentState(TypedDict):
    run_id: str
    user_request: str
    style_id: str | None
    target_platform: str
    topics: list[dict]
    selected_topic: dict | None
    outline: dict | None
    sub_queries: list[str]
    snippets: Annotated[list[dict], add]
    draft_md: str
    images: list[dict]
    review: dict | None
    revision_count: int
    config: dict
    error: str | None
```

图结构：
```
topic → planner → research(并行 fan-out) → editor → writer → illustrator → reviewer
                                                                              ↕
                                                                          reviser
```

条件边：
- `reviewer` → pass=true → END (status=done)
- `reviewer` → pass=false & revision_count < 2 → `reviser`
- `reviewer` → pass=false & revision_count ≥ 2 → END (status=needs_human)

Checkpointer: `PostgresSaver`。

### 5.2 `app/agents/topic.py` — 选题（§4.2）

| 输入 | 工具 | 输出 |
|---|---|---|
| user_request | `fetch_hotnews` + `web_search` | `topics: [{title, angle, why, keywords}]` |

去重：标题模糊匹配已有 runs。

### 5.3 `app/agents/planner.py` — 规划（§4.3）

| 输入 | 输出 |
|---|---|
| selected_topic + style_fingerprint | `outline: {sections: [...]}` + `sub_queries: [...]` |

### 5.4 `app/agents/researcher.py` — 研究（§4.4，并行）

PRD 明确用 LangGraph `Send` 实现 fan-out：

```python
def research_fanout(state):
    return [Send("research_worker", {"query": q}) for q in state["sub_queries"]]
```

每个 worker：`web_search(q)` → `scrape(top3_urls)` → 写 `snippets` 表 + pgvector embedding。

容错：单 worker 失败跳过；全部失败退化到 RAG 历史素材。

### 5.5 `app/agents/editor.py` — 编辑（§4.5）

整合 snippets → 修正大纲 → 输出最终 outline。

### 5.6 `app/agents/writer.py` — 写作（§4.6）

| 特征 | 实现 |
|---|---|
| 流式输出 | `LLMClient.stream("writer", ...)` |
| 风格注入 | prompt 中嵌入指纹 JSON + 范文片段 |
| 图片占位 | 输出 `[IMG:type:desc]`，≤3 张(<1500 字) / ≤5 张(1500–3000 字) |
| 平台适配 | 根据 target_platform 调整字数/tag/格式 |

### 5.7 `app/agents/illustrator.py` — 配图（§4.7）

完整 7 步：
1. 解析 `[IMG:type:desc]` + ±400 字上下文
2. 分类 5 路径（chart/cover/illustration/card/infographic）
3. LLM prompt 增强（中文→英文）
4. 查 image_cache → 命中复用
5. 未命中 → 调对应 tool（n=2 候选）
6. 倒序替换占位符为 `![alt](url)`
7. 写 `runs.images` JSONB

### 5.8 `app/agents/reviewer.py` — 审阅（§4.8）

评分 5 维度（结构/表达/事实/风格/图文一致性）。
图文一致性：Phase 1 LLM 文本判断（对比 alt + 上下文 vs 图片 prompt）。

输出：`{pass: bool, score: float, issues: [{type, severity, section, desc}]}`。

### 5.9 `app/agents/reviser.py` — 修订（§4.9）

接收 issues → 双策略：
1. 文本修改（首选）
2. 重新生图（仅 image_mismatch 且文本改不动时）

### 验收

- [ ] `--mock` 模式跑通全 8 节点
- [ ] 真 LLM 跑通 1 篇端到端（含选题、研究、写作、配图、审阅）
- [ ] 条件边正确：通过 → done / 不通过 → reviser → 再审
- [ ] `revision_count ≥ 2` → needs_human
- [ ] checkpoint 持久化：杀进程 → resume 继续
- [ ] `run_events` 含完整事件链（SSE 格式对照 PRD §6.4）
- [ ] Research fan-out 并行度可配（默认 5）
- [ ] 单 run 超 12min → 强杀

---

## Step 6 — REST API + SSE + Workers

对应 PRD: §6.4 REST API 设计 / §5.5 可观测

### 6.1 `app/workers/runner.py`

Celery task：启动 LangGraph `app_graph.astream()` → 实时写 `run_events` → 推 SSE。

### 6.2 `app/api/runs.py`

PRD §6.4 完整路由：

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/runs` | 创建并启动（下发 Celery task） |
| GET | `/api/runs` | 列表（?status=&limit=&offset=） |
| GET | `/api/runs/{id}` | 单条详情（含 cost + usage） |
| GET | `/api/runs/{id}/stream` | SSE 实时事件流 |
| GET | `/api/runs/{id}/events` | 历史事件 |
| POST | `/api/runs/{id}/interrupt` | 人工介入 |
| POST | `/api/runs/{id}/resume` | 继续 |
| POST | `/api/runs/{id}/abort` | 中止 |
| PUT | `/api/runs/{id}/article` | 编辑草稿 |
| POST | `/api/runs/{id}/complete` | 标记完成 |

SSE 事件格式严格按 PRD §6.4 的 event/data 格式。

### 6.3 `app/api/topics.py`

| GET | `/api/topics/candidates` | 调 hotnews + LLM 生成候选 |
| POST | `/api/topics/refresh` | 强制刷新 |

### 6.4 `app/api/styles.py`

CRUD + `POST /api/styles/{id}/analyze`（触发 `analyze_style`）。

### 6.5 `app/api/stats.py`

| GET | `/api/stats/dashboard` | 产出 / 成本 / pass 率聚合 |
| GET | `/api/stats/cost` | Per-agent 成本趋势 |

### 6.6 `app/api/settings.py`

读写 `config/models.yaml` 的运行时配置。

### 验收

- [ ] `POST /api/runs` → 返回 run_id + 异步启动
- [ ] `GET /api/runs/{id}/stream` → SSE 事件实时推送
- [ ] `POST /api/runs/{id}/abort` → run 停止
- [ ] `POST /api/runs/{id}/interrupt` + `resume` → checkpoint 恢复
- [ ] `GET /api/stats/dashboard` → 聚合数据正确
- [ ] OpenAPI 文档自动生成（`/docs`）

---

## Step 7 — 前端

对应 PRD: §4.14 前端关键页面 / §6.3 frontend 目录

### 技术栈（PRD §6.1）

Next.js 15 + Tailwind + shadcn/ui + TipTap + Zustand

### 7.1 Dashboard `/`（PRD §4.14 表格第 1 行）

选题候选卡片 / 运行中任务 / 最近文章 / KPI 数字（含成本统计）

### 7.2 New Run `/runs/new`（PRD §4.14 表格第 2 行）

选题确认 / 风格选择 / 平台 toggle / 模型选择 / 预算设置 / 开跑按钮

### 7.3 Run Live `/runs/{id}`（PRD §4.14 表格第 3 行）

7 节点 Timeline / 当前 token 流式预览 / per-agent 成本 / 控制按钮（pause/resume/abort）

组件：`AgentTimeline.tsx` + `CostDashboard.tsx`

SSE：EventSource 连 `/api/runs/{id}/stream`，事件格式严格对照 PRD §6.4。

### 7.4 Article Editor `/runs/{id}/edit`（PRD §4.14 表格第 4 行）

TipTap 富文本 / 配图栏 / 风格匹配雷达图 / 平台预览

组件：`DraftEditor.tsx` + `ImageGallery.tsx`

### 7.5 Style Manager `/styles`（PRD §4.14 表格第 5 行）

风格卡片网格 / 上传范文 / 指纹可视化（词云+句法图）

### 7.6 Settings `/settings`（PRD §4.14 表格第 6 行）

Provider 选择 / Agent 模型分配 / API Keys / 并发上限 / 预算阈值

### 验收

- [ ] 6 个页面路由切换正常
- [ ] Run Live 页面 SSE 实时事件 → 7 节点 Timeline 高亮
- [ ] Editor 富文本编辑 + 保存调 `PUT /api/runs/{id}/article`
- [ ] Dashboard 展示真实统计数据
- [ ] 响应式布局（桌面可用）
- [ ] `npm run build` 无错误

---

## Step 8 — 前后端联调 + 端到端验收

对应 PRD: §9.2 验收标准

### 8.1 全流程走查

1. 打开 Dashboard → 点"新建 Run"
2. 输入主题 → 选风格 → 启动
3. 跳转 Run Live → 看 SSE 7 节点推进
4. 完成后 → 点"编辑" → 修改文字 + 替换图片
5. 点"标记完成"
6. Dashboard 显示新 run
7. `/styles` 上传范文 → 触发分析
8. `/settings` 改预算 → 验证降级/熔断

### 8.2 异常路径验证

| 场景 | 期望（PRD §10.3） |
|---|---|
| Topic 失败 | 重试 1 次（换温度），仍失败让用户手填 |
| 单 Researcher 失败 | 跳过，其他继续 |
| 全部 Researcher 失败 | 退化到 RAG 历史素材 |
| Image 生成失败 | 重试 2 次换 provider |
| Reviewer pass=false | Reviser 修订 ≤2 次 |
| 超出 2 轮 | → needs_human |
| 超时 > 12min | → abort |
| 预算 80% | → 降级模型 |
| 预算 100% | → 熔断 |

### 8.3 性能验证（PRD §5.1）

| 指标 | 目标 |
|---|---|
| 端到端中位数 | ≤ 8 分钟 |
| 端到端 95p | ≤ 12 分钟 |
| 首屏加载 | ≤ 2s |
| SSE 延迟 | ≤ 200ms |
| 并发 5 run | 不死锁 |

### 8.4 PRD §9.2 验收清单

- [ ] 端到端 demo：一句话 → 8 分钟内完整图文（含 2~3 张配图）
- [ ] 6 个前端页面可用
- [ ] 单篇成本取决于 provider（Token Plan 内趋近 ¥0）
- [ ] 风格盲测识别率 < 70%
- [ ] 连续 50 次 run 成功率 ≥ 95%
- [ ] run_events 能回放任意一次 run（含 per-agent token 明细）
- [ ] Langfuse 能看到每次 LLM 调用 trace
- [ ] 预算熔断：80% 降级 / 100% 熔断
- [ ] 文档：OpenAPI 自动生成 + 部署文档

---

## 全步骤依赖关系

```
Step 1（骨架）
  ├── Step 2（数据库）
  ├── Step 3（LLM 层）
  │     └── Step 5 的所有 Agent 节点依赖 3
  └── Step 4（工具层）
        └── Step 5 的 Agent 依赖对应工具

Step 5（LangGraph + Agents）依赖 2 + 3 + 4
  └── Step 6（API + Workers）依赖 5

Step 7（前端）可与 Step 2~6 并行开发（用 mock）
  └── Step 8（联调）依赖 6 + 7
```

---

## 当前进度

| Step | 状态 |
|---|---|
| Step 1 骨架 | ⬜（后端部分已有基础，前端 + docker 未初始化） |
| Step 2 数据库 | ⬜（当前 SQLite 6 表可用；PRD 目标 PG 7 表） |
| Step 3 LLM 层 | ⬜（现有 `app/llm.py` 单 provider，PRD 要求多 provider） |
| Step 4 工具层 | 🟡（hotnews ✅，其余 7 个待写） |
| Step 5 LangGraph | ⬜ |
| Step 6 API + Workers | ⬜（路由壳已有，内部待重写） |
| Step 7 前端 | ⬜ |
| Step 8 联调验收 | ⬜ |
