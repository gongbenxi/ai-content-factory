# AI Content Factory — 实施计划 v2（LangGraph 原生重写）

> 现有 `app/agents/graph.py`、`app/services/runner.py`、`app/db.py`、`app/routers/*` 全部归档到 `app/_legacy/`，从零起步，按 PRD 目标架构直接落地 LangGraph + PG/pgvector + 多 Provider + 前端。

---

## 总原则

- **基础设施先到位**（PG+pgvector+Langfuse），再写一行代码
- **LangGraph 是骨架**，所有 agent 从第一天起就是 StateGraph node
- **每步都能独立验收**：可跑命令 / 可看输出，过不了不进下一步
- **mock 模式贯穿全程**：每个 agent 接受 `mock=True` 参数，前端 / API 不依赖真 LLM 也能联调

---

## Phase 0 — 推倒重来 + 基础设施（0.5 天）

### 0.1 归档旧代码

```bash
mkdir -p app/_legacy
mv app/agents/graph.py app/services/runner.py app/db.py app/routers app/_legacy/
```

保留 `app/tools/hotnews.py`（可复用）、`pyproject.toml`、`docker-compose.yml`、`config/`、`docs/`。

### 0.2 目录骨架（按 PRD §6.3 一次到位）

```
app/
├── main.py                  # FastAPI 入口
├── config.py                # Pydantic Settings 读 models.yaml + .env
├── agents/{graph,topic,planner,researcher,editor,writer,illustrator,reviewer,reviser}.py
├── tools/{hotnews,rss,style,search,scraper,rag,safety,image,image_cache}.py
├── llm/{client,budget,prompts/}.py
├── db/{schema.sql,session.py,models.py,migrations/}
├── api/{runs,topics,styles,stats,settings}.py
├── workers/runner.py        # LangGraph driver
└── observability/langfuse.py
config/models.yaml
frontend/                    # Vite + React 18 + TypeScript
tests/{tools,agents,api}/
```

### 0.3 依赖一次装齐

```bash
pip install -e .
pip install langgraph langgraph-checkpoint-postgres alembic feedparser tenacity \
            pyecharts playwright pydantic-settings sse-starlette pytest pytest-asyncio
playwright install chromium
```

### 0.4 起 docker

```bash
docker compose up -d postgres redis langfuse
docker exec -it $(docker compose ps -q postgres) psql -U acf -d acf -c "CREATE EXTENSION vector;"
```

### 验收

- [ ] `psql -h localhost -U acf -d acf -c "\dx"` 列出 `vector`
- [ ] `curl localhost:3000` Langfuse UI 可打开
- [ ] `tree app -L 2` 与上面骨架一致

---

## Phase 1 — DB Schema + 迁移（0.5 天）

### 1.1 `app/db/schema.sql`

照搬 PRD §4.12.2 的 7 表（runs / run_events / snippets / styles / style_samples / image_cache / token_usage），含 pgvector 索引。

### 1.2 `app/db/session.py`

SQLAlchemy 2.0 async + `psycopg`（与 pyproject.toml / PRD §4.12.1 一致）。

### 1.3 Alembic

```bash
alembic init app/db/migrations
# 把 schema.sql 转成 op.execute(...) 的 initial migration
alembic upgrade head
```

### 验收

- [ ] `alembic upgrade head` 成功，`\dt` 看到 7 张表
- [ ] `INSERT INTO runs(user_request, target_platform) VALUES('test', 'wechat') RETURNING id;` 通
- [ ] `SELECT '[1,2,3]'::vector(3);` 通

---

## Phase 2 — LLM 抽象层 + 可观测（1 天）

### 2.1 `config/models.yaml`

照搬 PRD §6.1（xiaomi/deepseek/openai 三 provider，7 agent 分配）。

### 2.2 `app/llm/client.py`

```python
class LLMClient:
    async def chat(self, agent: str, messages, **kw) -> str
    async def chat_json(self, agent: str, messages, schema) -> dict
    async def stream(self, agent: str, messages) -> AsyncIterator[str]
```

- 内部按 agent 查 `models.yaml` 路由 provider + tier
- `tenacity` 3 次指数退避，60s 超时
- 每次调用后写 `token_usage` 表（含 latency_ms）
- `mock=True` 走 fixture（写在 `app/llm/_mock.py`，按 agent 名返回桩响应）

### 2.3 `app/llm/budget.py`

双模式熔断（PRD §4.11.4）：
- **Token 模式**（Token Plan 内）：`max_tokens_per_run` 上限
- **金额模式**（付费 provider）：`budget_limit_cents` 上限
- 调用前查 `token_usage` 累计值
- ≥ 80% 把 tier 强制改 `fast`，发 `budget.warning` 事件
- ≥ 100% 抛 `BudgetExceeded`，保存当前中间状态

### 2.4 `app/observability/langfuse.py`

装饰器 `@trace_llm`，自动上报 prompt/completion/usage/latency 到 Langfuse。

### 2.5 Prompts

`app/llm/prompts/{topic,planner,researcher,editor,writer,reviewer,reviser,illustrator}.txt` —— 直接落 PRD §4.x 各章给的 system prompt。

### 验收

- [ ] `pytest tests/llm/test_client.py` —— 真 mock 调用 + token_usage 写入 + budget 熔断
- [ ] `python -c "import asyncio; from app.llm.client import LLMClient; print(asyncio.run(LLMClient().chat('topic',[{'role':'user','content':'hi'}])))"` 真 MiMo 返回
- [ ] Langfuse Dashboard 看到一条 trace

---

## Phase 3 — 工具层（1.5 天，可分批并行）

按依赖排序，每个工具单独可测：

| # | 文件 | 来源 / 实现 | 验收命令 |
|---|---|---|---|
| 3.1 | `tools/rss.py` | 从 `skills/rss_fetcher/` 提取 | `pytest -k rss` 返 ≥ 5 条 |
| 3.2 | `tools/style.py` | 从 `skills/style_fingerprint/` 提取 `StyleFingerprint` | 输入 1KB 中文 → 输出 fingerprint JSON |
| 3.3 | `tools/search.py` | Tavily API 封装 | `TAVILY_API_KEY=... pytest -k search` |
| 3.4 | `tools/scraper.py` | Crawl4AI 封装 | 抓 URL → markdown ≥ 200 字 |
| 3.5 | `tools/safety.py` | 自建敏感词表 | 命中关键词返 issue 列表 |
| 3.6 | `tools/rag.py` | BGE-M3 embed + pgvector；**双层检索**（PRD §4.12.3）：L1 `snippets` 表 24h 素材复用 + L2 `runs` 表 90d 历史避重 | upsert 3 条 → L1 search 命中 top-1；插入 done run → L2 search 命中 |
| 3.7 | `tools/image_cache.py` | SHA256 prompt_hash + image_cache 表 | 同 prompt 二次调 `hit_count` 自增 |
| 3.8 | `tools/image.py` | 五路径：chart(pyecharts+Playwright) / card(Pillow) / infographic(HTML+Playwright) / cover(硅基流动 Kolors) / illustration(FLUX.1-schnell)；含 `parse_placeholders` + `enhance_prompt` + `render_with_images` | `python -m app.tools.image --demo` 落盘 5 种 PNG |

每个工具配 `tests/tools/test_<name>.py`，CI 跑 `pytest tests/tools/` 全绿。

---

## Phase 4 — LangGraph 状态机 + 8 Agent（2 天）

> 8 个 agent 角色 / 8 个 graph node，前端 Timeline 展示 7 步（Reviser 归入 Reviewer 步骤）。

### 4.1 `app/agents/graph.py`

照 PRD §4.10 装配：

```python
class ContentState(TypedDict):
    # 输入
    run_id: str
    user_request: str
    user_preferences: dict             # {topics, styles, avoid_keywords}
    target_platform: str
    style_id: str | None

    # 中间产物
    topic: dict | None
    outline: list[dict] | None
    sub_queries: list[str] | None
    snippets: Annotated[list[dict], add]   # reducer 合并
    final_outline: dict | None
    draft_md: str | None
    images: list[dict]                 # IllustratorAgent 填充

    # 审阅
    review: dict | None
    revise_count: int

    # 计量
    cost_cents: int
    usage_by_agent: dict               # per-agent {input_tokens, output_tokens, cost_cents}
```

> 与 PRD §4.10 ContentState 完全一致。`image_prompts` 不单独存——从 `draft_md` 中解析 `[IMG:]` 占位符；`checkpoints` 由 LangGraph PostgresSaver 内部管理。

- `PostgresSaver.from_conn_string(PG_URL)` 做 checkpointer
- `research_dispatcher` 用 `Send` API fan-out
- `review_gate` 条件边：pass→END / fail&count<2→reviser / fail&count≥2→END(needs_human)

### 4.2 八个 agent 节点（每个一文件）

每个 node 同样的形状：

```python
async def topic_agent(state: ContentState, config) -> dict:
    llm = LLMClient()
    emit(state["run_id"], "agent.start", agent="topic")
    result = await llm.chat_json("topic", [...prompts + state...])
    emit(state["run_id"], "agent.done", agent="topic", output=result)
    return {"topic": result}
```

- 全部支持 `mock=True`（从 `app/llm/_mock.py` 取桩响应）
- `writer_agent` 用 `llm.stream()`，逐 token emit `agent.token` 事件
- `illustrator_agent` 走 Phase 3.8 的 7 步流程
- `reviewer_agent` 含图文一致性 LLM 文本判断（PRD §4.7.7 Phase 1）

### 4.3 CLI 驱动

```bash
python -m app.agents.graph --mock --user-request "随便写一篇"
python -m app.agents.graph --user-request "DeepSeek-V3 解读" --style caoz
python -m app.agents.graph --resume <run_id>
```

### 验收

- [ ] `--mock` 跑通：DB 出现 1 条 run（status=done），run_events 含 8 个 agent 的完整事件链
- [ ] 真 LLM 跑通：≥ 1500 字 markdown，images JSONB 含 ≥ 2 张
- [ ] 强制 reviewer 返 fail 两次 → status=needs_human
- [ ] 中途 `kill -9` 进程 → `--resume` 从最后 checkpoint 继续
- [ ] 单 run 超 15min → 自动 abort + 保存中间产物（PRD §5.1 硬超时）

---

## Phase 5 — FastAPI + SSE + 后台 Worker（1 天）

### 5.1 `app/main.py`

FastAPI app + CORS + 启动钩子（init DB pool）+ 挂载 5 个 router + 静态文件挂载 `frontend/dist`（Vite 构建产物）。

### 5.2 `app/workers/runner.py`

```python
async def start_run(run_id: str, mock: bool = False):
    async for state in graph.astream(initial_state, config={"configurable": {"thread_id": run_id}}):
        await write_event(run_id, state)   # 实时写 run_events + 推 SSE
```

FastAPI BackgroundTasks 调度（Phase 1 不上 Celery）。

### 5.3 `app/api/runs.py`（PRD §6.4 全套）

| Method | Path | 说明 |
|---|---|---|
| POST | `/api/runs` | 创建 + 后台启动 |
| GET | `/api/runs?status=&limit=` | 列表 |
| GET | `/api/runs/{id}` | 详情含 cost / usage_by_agent |
| GET | `/api/runs/{id}/stream` | **SSE 实时**（`sse_starlette`）|
| GET | `/api/runs/{id}/events?after_id=` | 历史回放 |
| POST | `/api/runs/{id}/interrupt` | LangGraph interrupt（Pause） |
| POST | `/api/runs/{id}/resume` | LangGraph resume，**body 可带 state patch**（PRD A3：编辑 state 后继续）|
| POST | `/api/runs/{id}/retry?from_agent=xxx` | **从指定 agent 重试**（PRD A1：不从头跑）|
| POST | `/api/runs/{id}/abort` | 强杀 |
| PUT | `/api/runs/{id}/article` | 编辑 draft_md |
| POST | `/api/runs/{id}/complete` | status→done |
| GET | `/api/runs/{id}/export?format=md` | 导出 markdown 文件（PRD M4）|

SSE 事件格式严格按 PRD §6.4。

### 5.4 其余 router

- `api/topics.py`：`GET /candidates`（调 hotnews + LLM 选题）、`POST /refresh`
- `api/styles.py`：CRUD + `POST /{id}/analyze`
- `api/stats.py`：`/dashboard`、`/cost`
- `api/settings.py`：读写 `models.yaml`

### 验收

- [ ] `uvicorn app.main:app` → `/docs` 可访问，OpenAPI 路由齐
- [ ] `curl -X POST /api/runs -d '{"user_request":"AI","mock":true}'` 返 run_id
- [ ] `curl -N /api/runs/{id}/stream` 实时收到 7 步 SSE 事件
- [ ] 断开 SSE 重连 → `?after_id=N` catch up 不丢事件
- [ ] `POST /interrupt` → `POST /resume`（带 state patch body）→ 从断点继续
- [ ] `POST /retry?from_agent=writer` → 从 writer 重跑，不重跑前面的 agent
- [ ] `GET /export?format=md` → 下载 markdown 文件

---

## Phase 6 — 前端 Vite + React（3 天）

技术栈：Vite + React 18 + TypeScript + React Router + Tailwind CSS + shadcn/ui + TipTap + Zustand + Recharts

> 纯 SPA，无 SSR 需求。Vite 构建快、配置轻，适合对接 FastAPI 后端。

### 6.1 初始化

```bash
npm create vite@latest frontend -- --template react-ts
cd frontend
npm i react-router-dom tailwindcss @tailwindcss/vite
npx shadcn@latest init
npm i @tiptap/react @tiptap/starter-kit zustand recharts
```

`vite.config.ts` 配 proxy 把 `/api` 转发到 `localhost:8000`（开发时免 CORS）。

### 6.2 路由结构

```
src/
├── routes/
│   ├── Dashboard.tsx          # /
│   ├── NewRun.tsx             # /runs/new
│   ├── RunLive.tsx            # /runs/:id
│   ├── ArticleEditor.tsx      # /runs/:id/edit
│   ├── StyleManager.tsx       # /styles
│   └── Settings.tsx           # /settings
├── components/
│   ├── AgentTimeline.tsx      # 7 节点进度 + token 实时
│   ├── DraftEditor.tsx        # TipTap 富文本
│   ├── ImageGallery.tsx       # 配图栏
│   ├── CostDashboard.tsx      # 成本看板
│   └── StyleRadar.tsx         # 风格雷达图
├── stores/                    # Zustand
├── hooks/useSSE.ts            # EventSource 封装
└── api/client.ts              # fetch 封装
```

### 6.3 优先级 P0：Run Live 页（`/runs/:id`）

- `AgentTimeline.tsx`：7 节点进度条 + 每节点 token 计数 + 流式 token 预览
- `useSSE` hook 连 `/api/runs/{id}/stream`，断开自动 `?after_id=N` catch up
- Pause / Resume / Abort 按钮
- 验收：浏览器开 → 后台 mock 跑 → 7 节点逐次点亮，token 流式增长

### 6.4 P0：Dashboard `/`

- 今日选题卡片（调 `/api/topics/candidates`）
- 进行中 runs + 最近完成
- KPI（成本 / 产出 / pass 率）
- 验收：点选题 → 跳 `/runs/new` 带参数

### 6.5 P1：New Run `/runs/new`

风格选择 + 平台 toggle + 预算 + 模型 → POST `/api/runs`。

### 6.6 P1：Editor `/runs/:id/edit`

TipTap + 配图栏（含 **备选图切换**：每张图有 N=2 候选，PRD §4.7）+ 风格匹配雷达图 + 平台预览。

### 6.7 P2：Style Manager `/styles` + Settings `/settings`

风格 CRUD + 上传范文触发分析；Settings 改 `models.yaml`。

### 验收

- [ ] 6 页路由切换流畅
- [ ] `npm run build` 无错，产物放 `frontend/dist/`
- [ ] FastAPI 静态文件挂载 `dist/` → 单端口 8000 同时服务前后端
- [ ] 端到端：浏览器一句话 → 8 分钟内拿到含 2~3 张图的文章

---

## Phase 7 — 端到端验收（0.5 天）

直接按 PRD §9.2 跑：

| 项 | 目标 | 检验方式 |
|---|---|---|
| 端到端中位耗时 | ≤ 8min | 连跑 10 篇统计 |
| 95p 耗时 | ≤ 12min | 同上 |
| 硬超时 15min | abort + 保存中间产物 | 设 `run_timeout=15` |
| 单 run 成功率 | ≥ 95% | 跑 50 次脚本 |
| **并发 5 run 不阻塞** | 通过 | 同时 POST 5 个 run，全部完成无死锁（PRD §2.2） |
| 预算 80% 降级 | 触发 | 设 `max_tokens_per_run=10000` |
| 预算 100% 熔断 | 触发 | 设更低；付费 provider 验证金额模式 |
| Reviewer 2 轮失败 → needs_human | 触发 | mock reviewer 强返 fail |
| 单 worker 失败跳过 | 触发 | mock scraper 抛异常 |
| **事实编造率 < 5%** | 通过 | 抽查 20 篇人工核验（PRD §2.2） |
| run_events 完整回放 | 通过 | `GET /events?after_id=0` |
| Langfuse 看 trace | 通过 | UI 检查 |
| 单篇成本 | Token Plan 内 ≈ ¥0 | `token_usage` 聚合 |
| **部署文档** | 齐全 | OpenAPI 自动生成 + README 部署步骤（PRD §9.2） |

---

## 时间表（理想，单人）

| Phase | 工期 | 累计 |
|---|---|---|
| 0 基础设施 | 0.5d | 0.5d |
| 1 DB Schema | 0.5d | 1d |
| 2 LLM 层 | 1d | 2d |
| 3 工具层 | 1.5d | 3.5d |
| 4 LangGraph + 8 Agent | 2d | 5.5d |
| 5 API + SSE | 1d | 6.5d |
| 6 前端 | 3d | 9.5d |
| 7 验收 | 0.5d | **10d** |

可并行优化：Phase 3 内 8 个工具可分两人 / 两天；Phase 6 前端可从 Phase 5 完成（SSE 通了）起并行。

---

## 关键风险点

1. **PostgresSaver checkpoint**：LangGraph 这个组件容易踩 schema 版本坑，建议 Phase 4 第一天就把"杀进程→resume"跑通，过不去回退用 `SqliteSaver`
2. **Tavily / 硅基流动 / Crawl4AI 三个外部 API**：尽早申请 key，Phase 3 没 key 就卡住
3. **BGE-M3 本地部署**：第一次模型下载 ~2GB，Phase 3.6 提前预热
4. **PRD vs 现实**：Vision 校验（Phase 2）、Celery 队列、多账号 —— **全部不在这个计划里**，PRD 已划到 Phase 2+

---

## 当前进度

| Phase | 状态 |
|---|---|
| 0 推倒重来 + 基础设施 | ✅（Docker 需手动安装） |
| 1 DB Schema | ✅ |
| 2 LLM 层 | ✅ |
| 3 工具层 | ✅ |
| 4 LangGraph + 8 Agent | ✅ |
| 5 API + SSE | ✅ |
| 6 前端 | ✅（基础骨架 + 6 页面路由 + 编译通过） |
| 7 验收 | ⬜ |
