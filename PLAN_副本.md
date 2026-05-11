# AI Content Factory 后端实施计划

## 技术决策（已确认）

| 项 | 决策 |
|---|---|
| 数据库 | SQLite（`app/app.db`） |
| 向量检索 | Phase 1 不做，选题去重用标题模糊匹配 |
| LLM | 小米 MiMo（OpenAI 兼容，`token-plan-cn.xiaomimimo.com/v1`） |
| 主力模型 | MiMo-V2.5-Pro（写作/审阅/编辑） |
| 轻量模型 | MiMo-V2.5（选题/研究） |
| Web 框架 | FastAPI + Uvicorn |
| 认证 | 不做，本地单用户 |
| 配图 | 只生成 prompt 占位符 |
| 发布 | 不做，到"标记完成 + 导出 md" |

---

## Step 1 — LLM 抽象层 `app/llm.py`

- [x] 创建文件骨架
- [x] 修正 base_url → `https://token-plan-cn.xiaomimimo.com/v1`
- [x] 修正模型名 → `MiMo-V2.5-Pro` / `MiMo-V2.5`
- [x] 验证 `chat()` / `chat_json()` / `stream()` 三个方法

## Step 2 — 数据库 `app/db.py`

- [x] 创建 `db.py`：SQLite 连接 + WAL 模式
- [x] 建表：`runs`（运行记录）
- [x] 建表：`run_events`（事件流，SSE 回放用）
- [x] 建表：`snippets`（研究素材）
- [x] 建表：`styles`（风格指纹）
- [x] 建表：`style_samples`（风格样本文章）
- [x] `init_db()` 函数：启动时自动建表
- [x] 基础 CRUD 工具函数

## Step 3 — Agent 改造 `app/agents/graph.py`

- [x] 创建 `AgentLLM` 统一接口（真 API + Mock 双模式）
- [x] 写好各 Agent 的 system prompt（`PROMPTS` 字典）
- [x] 改造 `topic_agent`：接真实 prompt，输出选题 JSON
- [x] 改造 `planner_agent`：输出大纲 + 子查询 JSON
- [x] 改造 `editor_agent`：接收 snippets，输出最终大纲
- [x] 改造 `writer_agent`：流式写作，输出 markdown
- [x] 改造 `reviewer_agent`：审阅打分 JSON
- [x] 改造 `reviser_agent`：根据 issues 修订
- [x] `research_dispatcher` 保持并发结构
- [x] 更新 CLI：加 `--mock` 参数
- [x] 冒烟测试：`--mock` 模式通过
- [x] 冒烟测试：真 MiMo API 模式通过

## Step 4 — Pydantic 模型 `app/models.py`

- [x] `CreateRunRequest`（创建运行请求）
- [x] `RunResponse`（运行详情响应）
- [x] `RunListResponse`（运行列表）
- [x] `TopicCandidate`（候选选题）
- [x] `StyleResponse`（风格详情）
- [x] `DashboardStats`（仪表盘统计）
- [x] `SettingsResponse`（系统配置）

## Step 5 — 后台任务 `app/services/runner.py`

- [x] `start_run()`：后台启动 graph，写 DB，推 SSE
- [x] 事件写入 `run_events` 表
- [x] 运行状态实时更新 `runs` 表
- [x] 异常处理：失败写 error 字段

## Step 6 — FastAPI 路由

### 6a. `app/routers/runs.py`
- [x] `POST /api/runs` — 创建并启动生成
- [x] `GET  /api/runs` — 列表（分页+筛选）
- [x] `GET  /api/runs/{id}` — 单条详情
- [x] `GET  /api/runs/{id}/events` — SSE 实时事件流
- [x] `GET  /api/runs/{id}/events/history` — 历史事件
- [x] `POST /api/runs/{id}/abort` — 中止
- [x] `PUT  /api/runs/{id}/article` — 编辑草稿
- [x] `POST /api/runs/{id}/complete` — 标记完成

### 6b. `app/routers/topics.py`
- [x] `GET  /api/topics/candidates` — 今日候选选题
- [x] `POST /api/topics/refresh` — 刷新选题

### 6c. `app/routers/styles.py`
- [x] `GET    /api/styles` — 列表
- [x] `GET    /api/styles/{id}` — 详情
- [x] `POST   /api/styles` — 新建
- [x] `PUT    /api/styles/{id}` — 更新
- [x] `DELETE /api/styles/{id}` — 删除
- [x] `POST   /api/styles/{id}/samples` — 上传范文
- [x] `POST   /api/styles/{id}/analyze` — 触发指纹分析

### 6d. `app/routers/stats.py`
- [x] `GET /api/stats/dashboard` — 仪表盘聚合数据

### 6e. `app/routers/settings.py`
- [x] `GET /api/settings` — 读取配置
- [x] `PUT /api/settings` — 更新配置

## Step 7 — 主入口 `app/main.py`

- [x] FastAPI app 实例 + CORS
- [x] 挂载所有 router
- [x] 启动时 `init_db()`
- [x] 静态文件服务（预留前端 dist/）
- [x] CLI：`uvicorn app.main:app --reload`

## Step 8 — 端到端验证

- [x] `pip install fastapi uvicorn openai` 依赖安装
- [x] `python -m app.agents.graph --mock` 通过
- [x] `export MIMO_API_KEY=... && python -m app.agents.graph` 真 LLM 通过
- [x] `uvicorn app.main:app` 启动成功
- [x] `POST /api/runs` 创建运行 → SSE 事件流正常
- [x] `GET /api/runs` 列表返回
- [x] `GET /api/styles` 风格列表返回
- [x] `GET /api/stats/dashboard` 统计数据正确

---

## 文件结构（最终）

```
app/
├── main.py                 # FastAPI 入口
├── llm.py                  # LLM 抽象层         ← Step 1
├── db.py                   # SQLite 建表+CRUD    ← Step 2
├── models.py               # Pydantic 模型       ← Step 4
├── app.db                  # 运行时生成
├── agents/
│   ├── __init__.py
│   └── graph.py            # 多 Agent 流水线     ← Step 3
├── routers/
│   ├── runs.py             # /api/runs/*         ← Step 6a
│   ├── topics.py           # /api/topics/*       ← Step 6b
│   ├── styles.py           # /api/styles/*       ← Step 6c
│   ├── stats.py            # /api/stats/*        ← Step 6d
│   └── settings.py         # /api/settings       ← Step 6e
└── services/
    └── runner.py            # 后台运行管理        ← Step 5
```

---

## 当前进度

**Phase 1 后端全部 8 个 Step 已完成** ✅
