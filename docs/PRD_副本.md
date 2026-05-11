# AI Content Factory — Phase 1 PRD
## 多 Agent 化版本 v1.0

| 项目代号 | AI Content Factory (ACF) |
|---|---|
| 版本 | Phase 1 — v1.0 |
| 日期 | 2026-05-08 |
| 状态 | Draft（待评审） |
| 作者 | 产品 + 工程 |
| 关联文档 | `docs/design-mockups.html`（高保真 UI）/ `app/agents/graph.py`（骨架代码） |

---

## 1. 产品概述

### 1.1 项目背景

随着大模型能力成熟与中文社交平台（公众号、小红书、抖音）内容供给爆炸，"AI 协助创作"已经从玩具走向生产工具。但当前直接用 ChatGPT/Claude 写稿的方式存在 **4 个结构性问题**：

1. **风格扁平化**：单 prompt 写出来的稿子模板感重，模仿不出特定 KOL 的语感与节奏
2. **事实幻觉**：尤其中文素材薄弱，时事类内容容易胡编
3. **图文割裂**：配图自己生成、文章自己生成，图与正文经常对不上号
4. **平台规范错配**：每个平台的字数、tag、首图、敏感词规则差异大，单稿适配成本高

### 1.2 产品愿景

> **让一个有内容直觉的运营，一个人能撑起以前 5 人小编团队的产能，且产出质量稳定不掉档。**

ACF 的核心思路：用**多 Agent 协同**模仿真人内容团队（主编→记者→写手→插画师→审稿）的工作流程，端到端产出"可直接发"的图文。

### 1.3 目标用户

| 优先级 | 角色 | 场景 |
|---|---|---|
| **P0** | 内容主理人 / 自媒体运营 / 公司新媒体 | 每天产出 1~3 篇符合品牌调性的图文 |
| **P1** | 个人 KOL | 用自己的风格量产，扩大产能 |
| **P1** | MCN 内容主管 | 多账号矩阵的批量内容供应 |
| 暂不覆盖 | 视频脚本 / 学术论文 / 长篇深度报道 | Phase 2+ 再考虑 |

### 1.4 范围界定（In Scope / Out of Scope）

**Phase 1 包含**：
- ✅ 7 个 Agent 多角色协同生成
- ✅ 中文热点采集（复用现有 6 个 skill）
- ✅ 风格指纹模仿（复用 style_fingerprint）
- ✅ 配图生成（复用 image-gen-coze）
- ✅ Reviewer 审阅 + 自动修订闭环
- ✅ Web Dashboard（运行控制 + 文章管理）
- ✅ 草稿落库 + 编辑器二次修改

**Phase 1 不包含（Phase 2+）**：
- ❌ 直接发布到小红书/公众号（仅留草稿，发布手动）
- ❌ 多账号矩阵
- ❌ 数据回流（阅读量、点赞）
- ❌ A/B 测试
- ❌ 移动端

---

## 2. 业务目标与成功指标

### 2.1 北极星指标

> **单运营人员日均产出可发布草稿数 ≥ 8 篇**（目前业内同等质量水平：3~4 篇/人/天）

### 2.2 关键指标

| 类别 | 指标 | Phase 1 目标 | 验证方式 |
|---|---|---|---|
| **效率** | 单篇生成耗时（端到端） | ≤ 8 分钟 | 系统埋点 |
| **效率** | 95p 耗时 | ≤ 12 分钟 | 系统埋点 |
| **成本** | 单篇 LLM + 图像总成本 | ≤ ¥3 | Langfuse 成本统计 |
| **质量** | 事实编造率 | < 5% | 抽查 20 篇人工核验 |
| **质量** | 风格盲测识别率 | < 70% | 朋友盲测 50 组 |
| **质量** | 图文一致 Reviewer 自动 pass 率 | ≥ 80% | Reviewer 日志 |
| **稳定** | 单次运行成功率（含修订） | ≥ 95% | LangGraph run_status |
| **稳定** | 同时跑 5 个 run 不互相阻塞 | 通过 | 压测 |

---

## 3. 用户故事

### 3.1 主路径（Must-have）

| ID | 用户故事 | 验收标准 |
|---|---|---|
| **M1** | 作为运营，我希望在 Dashboard 看到今天值得写的 3-5 个候选选题，点击其中一个就能开跑 | 候选选题来自当日热榜聚合，已排除最近 30 天写过的，按用户偏好排序 |
| **M2** | 作为运营，我希望看到 7 个 Agent 的实时进度（像快递物流），知道现在卡在哪一步 | SSE 推送 agent_start / token / tool_call / agent_done 事件，前端 Timeline 渲染 |
| **M3** | 作为运营，我希望收到草稿后能在编辑器里直接改、替换配图、看到风格匹配分数 | 富文本编辑器 + 配图替换面板 + 风格指纹对比雷达图 |
| **M4** | 作为运营，我希望标记"通过"后入文章库，导出 markdown 或后续接发布 | 状态机：drafting → reviewing → done，导出 .md / .docx |
| **M5** | 作为运营，我希望在风格管理里上传一个公众号文章 URL，自动抽取风格指纹 | URL → 抓取 → 调 style_fingerprint → 入库；最低 5 篇样本 |

### 3.2 异常路径（Should-have）

| ID | 用户故事 | 验收标准 |
|---|---|---|
| **A1** | 中途某个 Agent 失败 → 看到错误，能重试该 Agent 而不是从头跑 | LangGraph checkpoint + UI 上"Retry from XXX"按钮 |
| **A2** | Reviewer 不通过 → 自动 Reviser 修订，2 次后还不行让人介入 | max_revise_rounds=2，超出后状态置 `needs_human` |
| **A3** | 想中途停下来手动改大纲 → Pause / Edit / Resume | LangGraph 的 interrupt API + 前端 state 编辑面板 |
| **A4** | 某个外部 API 限流 → 退避重试，不打断整体 | tenacity 重试装饰器 + 错误事件流 |

### 3.3 长期演进（Nice-to-have，Phase 1 不实现但留接口）

| ID | 用户故事 |
|---|---|
| **N1** | 自动按发布日历排期 |
| **N2** | 多账号风格切换 |
| **N3** | 阅读量回流后自动调优 prompt |
| **N4** | 团队多人协作（评论、@） |

---

## 4. 功能需求详述

### 4.1 选题模块（TopicAgent）

**输入**：
- 用户偏好画像 `{topics: [], styles: [], avoid_keywords: []}`
- 当日热榜（来自 6 个采集 skill 聚合）
- 用户文本指令（可选，如"今天写点 AI 圈的"）

**处理**：
1. 调用 `fetch_hotnews_unified` 拿当日热榜 100 条
2. `vector_search_history(query=topic_title, k=5)` 排除最近 30 天写过的
3. 按用户偏好领域过滤
4. LLM 选出最适合的 3~5 条，每条生成 2 个不同切入角度

**输出**：
```json
{
  "candidates": [
    {
      "title": "DeepSeek-V3 发布带来的国产大模型竞争格局变化",
      "angle": "技术拐点 + 商业影响双线",
      "target_platform": "wechat",
      "hook": "开头钩子建议",
      "estimated_quality": 0.85
    }
  ]
}
```

**UI**：Dashboard 顶部"今日选题"卡片列表，点击 → 进入 New Run。

---

### 4.2 规划模块（PlannerAgent）

**输入**：选定的 Topic 对象

**处理**：LLM 推理生成大纲 + 子查询，遵循 GPT-Researcher 的"5 角度覆盖"原则：
- 背景 / 数据 / 案例 / 反方观点 / 未来趋势

**输出**：
```json
{
  "outline": [
    {"section": "DeepSeek-V3 性能数据", "intent": "建立技术事实"},
    {"section": "对比 GPT-4o 和 Claude Sonnet", "intent": "横向参照"}
  ],
  "sub_queries": ["DeepSeek-V3 在 MMLU/HumanEval 等基准的具体得分", "..."]
}
```

**约束**：3 ≤ outline ≤ 6 节；3 ≤ sub_queries ≤ 7 条。

---

### 4.3 研究模块（ResearcherAgent，并行）

**输入**：1 个 sub_query（每个 worker 一个）

**处理**（每个 worker 独立）：
1. `web_search(query, k=5)` —— Tavily 优先
2. 对前 3 条 `scrape_url` 拿正文
3. `vector_search_history(query, k=3)` 看历史素材有没有可复用的
4. LLM 从中筛 3~5 条"最有价值"的 snippet

**输出**：
```json
{
  "snippets": [
    {
      "source": "https://...",
      "title": "...",
      "excerpt": "...",
      "credibility": 0.85,
      "angle": "数据"
    }
  ]
}
```

**关键**：N 个 worker **并行执行**（参考 GPT-Researcher 的 multi_agents 模式）。

---

### 4.4 编辑模块（EditorAgent）

**输入**：原始 outline + 所有 snippets

**处理**：
1. 加载用户选定的 `style_fingerprint`
2. LLM 综合素材调整大纲（删/合/补节）
3. 决定每节引用哪几条 snippet
4. 输出"最终大纲 + 引用关系"

**输出**：
```json
{
  "final_outline": [
    {
      "section": "...",
      "intent": "...",
      "cite_snippet_ids": [3, 7, 12],
      "target_words": 400
    }
  ],
  "style_adjustments": "..."
}
```

---

### 4.5 写作模块（WriterAgent）

**输入**：final_outline + snippets + 风格指纹

**处理**：
- 系统提示包含风格指纹（句法特征、高频词、修辞偏好、5 条样本句）
- **启用 Anthropic Prompt Cache**（系统提示 1 小时缓存，省 70%+ token）
- 在每段末尾输出 `[IMG: <场景描述> | <ratio>]` 占位符给插画师

**输出**：
```markdown
# 标题

## 第一节
正文...
[IMG: DeepSeek 团队发布会场景 | 16:9]

## 第二节
...
[IMG: 国内 AI 公司对比示意 | 3:4]
```

**约束**：单篇 1500~2500 字（公众号默认）；2~4 张配图。

---

### 4.6 配图模块（IllustratorAgent）

**输入**：从草稿里解析出的 image_prompts

**处理**：
1. 对每个占位符调 `gen_image_seedream`（默认）或 Flux
2. 上传到对象存储（MinIO/OSS）
3. 替换草稿里的占位符为实际 URL

**输出**：
```json
{
  "images": [
    {
      "para_id": 1,
      "prompt": "...",
      "url": "https://...",
      "ratio": "16:9",
      "alt": "DeepSeek 发布会现场"
    }
  ]
}
```

---

### 4.7 审阅模块（ReviewerAgent）

**输入**：完整草稿 + 所有图片

**处理**：
1. **内容安全**：调 `content_safety_check`（敏感词库 + 阿里云内容安全）
2. **图文一致性**：每张图调 `image_consistency_check`（Claude Vision 看图能不能对应文字）
3. **风格匹配**：对比草稿和风格指纹的统计特征
4. **平台规范**：字数、emoji 用量、tag 数量是否符合目标平台
5. LLM 综合打分 + 列举 issues

**输出**：
```json
{
  "pass": false,
  "score": 6.8,
  "issues": [
    {"type": "image_mismatch", "para_id": 2, "detail": "图描绘的是发布会，但段落讲商业影响"},
    {"type": "style_drift", "detail": "结尾过于客观，原作者偏煽情"}
  ]
}
```

**通过阈值**：score ≥ 7.5 且 issues 中无 P0 类型。

---

### 4.8 修订模块（ReviserAgent）

**输入**：当前草稿 + Reviewer 的 issues

**处理**：LLM 针对每条 issue 做精修（不重写整篇）

**输出**：修订后的草稿，回到 Reviewer 二审

**循环上限**：`max_revise_rounds=2`，超出 → 状态 `needs_human`，UI 弹人工介入。

---

### 4.9 数据层

#### 4.9.1 技术选型：SQLite（Phase 1）

Phase 1 使用 SQLite（WAL 模式），理由：
- 单用户本地项目，无并发压力
- 零部署，`app.db` 一个文件
- 与现有 Skills_Repo 风格一致（12 个 skill 全用 SQLite）
- 后续需要向量检索时可平滑迁移至 PostgreSQL + pgvector

#### 4.9.2 Schema

```sql
-- 1. 运行记录（核心表）
CREATE TABLE runs (
    id              TEXT PRIMARY KEY,
    user_request    TEXT NOT NULL,
    style_id        TEXT DEFAULT 'default',
    target_platform TEXT DEFAULT 'wechat',
    status          TEXT DEFAULT 'pending',
    -- pending → running → reviewing → needs_human → done → failed
    current_agent   TEXT,
    config          TEXT DEFAULT '{}',
    topic           TEXT,              -- JSON
    outline         TEXT,              -- JSON
    snippets_count  INTEGER DEFAULT 0,
    draft_md        TEXT,
    final_md        TEXT,
    images          TEXT DEFAULT '[]', -- JSON
    review          TEXT,              -- JSON
    revise_count    INTEGER DEFAULT 0,
    cost_cents      INTEGER DEFAULT 0,
    error           TEXT,
    started_at      TEXT,
    ended_at        TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

-- 2. 运行事件流（SSE 回放用）
CREATE TABLE run_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     TEXT NOT NULL REFERENCES runs(id),
    ts         REAL NOT NULL,
    type       TEXT NOT NULL,
    data       TEXT DEFAULT '{}',
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_events_run ON run_events(run_id, ts);

-- 3. 研究素材
CREATE TABLE snippets (
    id          TEXT PRIMARY KEY,
    run_id      TEXT NOT NULL REFERENCES runs(id),
    query       TEXT,
    source_url  TEXT,
    title       TEXT,
    excerpt     TEXT,
    full_text   TEXT,
    credibility REAL DEFAULT 0.5,
    angle       TEXT,
    fetched_at  TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_snippets_run ON snippets(run_id);

-- 4. 风格指纹
CREATE TABLE styles (
    id              TEXT PRIMARY KEY,
    display_name    TEXT NOT NULL,
    category        TEXT DEFAULT '',
    fingerprint     TEXT DEFAULT '{}',
    sample_count    INTEGER DEFAULT 0,
    total_generated INTEGER DEFAULT 0,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

-- 5. 风格样本文章
CREATE TABLE style_samples (
    id         TEXT PRIMARY KEY,
    style_id   TEXT NOT NULL REFERENCES styles(id),
    source_url TEXT,
    title      TEXT,
    content    TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE INDEX idx_samples_style ON style_samples(style_id);
```

#### 4.9.3 选题去重策略（Phase 1）

Phase 1 不做向量检索，使用标题模糊匹配（Python `difflib.SequenceMatcher`）：
- 新选题 vs 最近 30 天已生成文章标题，相似度 > 0.6 视为重复
- Phase 2 引入 pgvector 后升级为语义相似度检索

---

### 4.10 前端关键页面（详见 `design-mockups.html`）

| 页面 | 路由 | 核心 UI 要素 |
|---|---|---|
| **Dashboard** | `/` | 选题候选卡片、运行中任务、最近文章、KPI 数字 |
| **New Run** | `/runs/new` | 选题确认、风格选择、平台 toggle、高级参数、开跑按钮 |
| **Run Live** | `/runs/{id}` | 7 节点 Timeline、当前 token 流式预览、控制按钮（pause/resume/abort） |
| **Article Editor** | `/articles/{id}` | TipTap 富文本、配图栏、风格匹配雷达图、平台预览 |
| **Style Manager** | `/styles` | 风格卡片网格、上传范文、指纹可视化（词云+句法图） |
| **Settings** | `/settings` | 模型选择、API Keys、并发上限、预算阈值 |

---

## 5. 非功能需求

### 5.1 性能

| 项 | 目标 |
|---|---|
| 单次端到端耗时（中位数） | ≤ 8 分钟 |
| 单次端到端耗时（95p） | ≤ 12 分钟 |
| Web Dashboard 首屏 | ≤ 2s |
| SSE 事件延迟 | ≤ 200ms |
| 并发 run 上限 | 3（单机） |

### 5.2 成本

| 项 | 目标 |
|---|---|
| 单篇 LLM 成本 | MiMo Token Plan 内，趋近 ¥0 |
| 单篇图像成本 | SiliconFlow 免费额度内，趋近 ¥0 |
| 模型分级 | Researcher = MiMo-V2.5（轻量）；Writer/Editor/Reviewer = MiMo-V2.5-Pro |

### 5.3 数据安全

- API Key 通过环境变量注入，**绝不入 git**
- 用户上传素材本地存储，不外发
- 生成的配图保存在本地 `data/images/` 目录

### 5.4 合规

- Phase 1 使用简单敏感词库做内容安全检查
- 不做"伪造身份发文"（模仿风格 OK，不署他人名）
- 配图提示词加 `non-celebrity, no real person face` 避免肖像权问题

### 5.5 可观测

- 所有 Agent 事件写入 `run_events` 表，支持完整回放
- 每个 run 记录成本、耗时、状态变更
- Phase 2 接 Langfuse 做 LLM trace

---

## 6. 技术架构

### 6.1 技术栈选型

| 层 | 选型 | 理由 |
|---|---|---|
| **Web 框架** | FastAPI + Uvicorn | async 原生；自动 OpenAPI 文档；SSE 支持 |
| **Agent 编排** | 自研 `graph.py`（Phase 1）→ LangGraph（Phase 2） | Phase 1 轻量可控；代码结构已按 LangGraph 对齐，迁移成本低 |
| **LLM** | 小米 MiMo（OpenAI 兼容格式） | Token Plan 700M credits 免费；V2.5-Pro 性能对标 GPT-4o |
| **LLM 抽象** | 自研 `llm.py`（OpenAI SDK） | 统一接口，改环境变量即可切 Anthropic/OpenAI/DeepSeek |
| **主力模型** | MiMo-V2.5-Pro | Writer/Editor/Reviewer 等核心 Agent |
| **轻量模型** | MiMo-V2.5 | Topic/Researcher 等非核心 Agent，省 token |
| **图像生成** | 硅基流动 SiliconFlow（FLUX.1-schnell 免费 / Seedream 付费） | 国内可用；OpenAI 兼容格式；免费额度够 Phase 1 |
| **数据库** | SQLite（WAL 模式） | 零部署；单文件；Phase 2 可迁 PG |
| **异步任务** | FastAPI BackgroundTasks + asyncio | 进程内异步，无需 Redis/Celery |
| **实时推送** | SSE（Server-Sent Events） | 浏览器原生支持；比 WebSocket 简单 |
| **热榜采集** | 从 Skills_Repo 集成（baidu/weibo/rss 等） | 纯 Python，零外部依赖 |
| **风格分析** | 从 Skills_Repo 集成（style_fingerprint） | 纯 Python，无 jieba 依赖 |
| **前端** | Vue 3 + Vite + Tailwind（Phase 1）→ 可换 Next.js | 与 design-mockups.html 的 Tailwind 风格一致 |

### 6.2 架构图

```
┌─────────── Browser (Vue 3 SPA) ──────────┐
│  Dashboard | NewRun | RunLive | Editor    │
│  StyleManager | Settings                  │
└──────────────────┬───────────────────────┘
                   │ REST + SSE
┌──────────────────▼───────────────────────┐
│           FastAPI Backend                 │
│                                           │
│  ┌─────────────────────────────────────┐ │
│  │  Agent Graph (graph.py)              │ │
│  │  Topic → Planner → Research(N并行)   │ │
│  │  → Editor → Writer → Illustrator     │ │
│  │  → Reviewer ↔ Reviser               │ │
│  └────────────┬────────────────────────┘ │
│               │                           │
│  ┌────────────▼────────────────────────┐ │
│  │  Tools Layer (app/tools/)            │ │
│  │  ├─ hotnews.py    ← 百度/微博/RSS   │ │
│  │  │                  (集成自 Skills)   │ │
│  │  ├─ style.py      ← 风格指纹分析     │ │
│  │  │                  (集成自 Skills)   │ │
│  │  ├─ web_search.py ← MiMo 联网搜索    │ │
│  │  ├─ image_gen.py  ← SiliconFlow API  │ │
│  │  │                  (FLUX / Seedream) │ │
│  │  └─ safety.py     ← 敏感词检查       │ │
│  └────────────┬────────────────────────┘ │
│               │                           │
│  ┌────────────▼────────────────────────┐ │
│  │  LLM Layer (app/llm.py)             │ │
│  │  OpenAI SDK → MiMo API              │ │
│  │  (可切换: Anthropic/OpenAI/DeepSeek) │ │
│  └─────────────────────────────────────┘ │
│                                           │
│  SQLite (app.db)  +  data/images/         │
└───────────────────────────────────────────┘
```

### 6.3 Skills_Repo 集成方案

**原则**：把需要的 Skill 代码直接搬进 `app/tools/`，不再依赖外部 Skills_Repo 路径。

#### 6.3.1 Phase 1 集成清单

| 来源 Skill | 集成到 | 核心逻辑 | 行数 |
|---|---|---|---|
| `baidu-hot-cn-1` | `app/tools/hotnews.py` | urllib 请求百度热搜 API | ~136 |
| `weibo-fresh-posts-0` | `app/tools/hotnews.py` | urllib 请求微博热搜 API | ~200 |
| `rss_fetcher` | `app/tools/hotnews.py` | 解析 RSS feed | ~300 |
| `style_fingerprint` | `app/tools/style.py` | 中文文本风格分析（句长、反问率、高频词） | ~467 |

#### 6.3.2 Phase 2 补充

| 来源 Skill | 说明 |
|---|---|
| `zhihu-fetcher` | 需 Node.js，Phase 2 改写为纯 Python |
| `toutiao-news-trends-0` | 需 Node.js，Phase 2 改写 |
| `douyin-hot-trend-1` | 需 Node.js，Phase 2 改写 |

#### 6.3.3 不集成

| Skill | 原因 |
|---|---|
| `image-gen-coze-1.1.3` | 用 SiliconFlow 替代 |
| `coze-workflow-1.1.3` | Phase 1 不需要 |
| `ec_creator` | 电商文案，非主流程 |
| `weibo-publisher` | 发布功能 Phase 2 |
| `longtask_system` | 用 FastAPI BackgroundTasks 替代 |

### 6.4 图像生成方案

#### 6.4.1 流程

```
Writer 输出草稿，在需要配图处插入占位符：
  [IMG: DeepSeek 性能对比柱状图，扁平科技风 | 16:9]

      ↓ IllustratorAgent 解析占位符

对每个占位符：
  1. 构造英文 prompt（LLM 翻译 + 增强）
  2. 调 SiliconFlow API 生成图片
  3. 保存到 data/images/{run_id}_{para_id}.png
  4. 替换占位符为本地路径

      ↓ ReviewerAgent 检查图文一致性
```

#### 6.4.2 图像 API 选型

| Provider | 模型 | 价格 | 说明 |
|---|---|---|---|
| **硅基流动 SiliconFlow** | FLUX.1-schnell | 免费（限速） | 速度快，质量中等，Phase 1 默认 |
| 硅基流动 SiliconFlow | FLUX.1-dev | ¥0.06/张 | 质量更好 |
| 硅基流动 SiliconFlow | Seedream 3.0 | ¥0.04/张 | 字节跳动出品，中文理解好 |
| 备选 | MiMo-V2-Omni | Token Plan 内 | 多模态模型，可做图文一致性校验 |

#### 6.4.3 API 调用示例

```python
# SiliconFlow 兼容 OpenAI Images API
from openai import AsyncOpenAI

client = AsyncOpenAI(
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1",
)

response = await client.images.generate(
    model="black-forest-labs/FLUX.1-schnell",
    prompt="A flat-style tech comparison bar chart...",
    size="1024x576",   # 16:9
    n=1,
)
image_url = response.data[0].url
```

#### 6.4.4 图文一致性校验

Phase 1 方案：由 ReviewerAgent 在审阅时用 LLM 判断图片描述与段落内容是否匹配（纯文本层面，不做 Vision 校验）。Phase 2 接入 MiMo-V2-Omni 做真实 Vision 校验。

### 6.5 后端文件结构

```
app/
├── main.py                 # FastAPI 入口 + CORS + 静态文件
├── llm.py                  # LLM 抽象层（OpenAI SDK → MiMo）
├── db.py                   # SQLite 连接 + 建表 + CRUD
├── models.py               # Pydantic 请求/响应模型
├── app.db                  # 运行时自动生成
│
├── agents/
│   ├── __init__.py
│   ├── graph.py            # 7 Agent 流水线编排
│   └── prompts.py          # 各 Agent 的 system prompt
│
├── tools/                  # 工具层（集成自 Skills_Repo）
│   ├── __init__.py
│   ├── hotnews.py          # 热榜聚合（百度/微博/RSS）
│   ├── style.py            # 风格指纹分析
│   ├── image_gen.py        # 图像生成（SiliconFlow）
│   ├── web_search.py       # 网页搜索
│   └── safety.py           # 内容安全检查
│
├── routers/                # FastAPI 路由
│   ├── runs.py             # /api/runs/*
│   ├── topics.py           # /api/topics/*
│   ├── styles.py           # /api/styles/*
│   ├── stats.py            # /api/stats/*
│   └── settings.py         # /api/settings
│
├── services/
│   └── runner.py           # 后台任务管理（启动 graph、写 DB、推 SSE）
│
└── data/
    └── images/             # 生成的配图存放目录
```

### 6.6 REST API 设计

#### 6.6.1 Runs（生成任务）

| 方法 | 路径 | 说明 |
|---|---|---|
| `POST` | `/api/runs` | 创建并启动一次生成 |
| `GET` | `/api/runs` | 列表（`?status=&limit=&offset=`） |
| `GET` | `/api/runs/{id}` | 单条详情 |
| `GET` | `/api/runs/{id}/events` | SSE 实时事件流 |
| `GET` | `/api/runs/{id}/events/history` | 历史事件（回放用） |
| `POST` | `/api/runs/{id}/abort` | 中止运行 |
| `PUT` | `/api/runs/{id}/article` | 编辑草稿 |
| `POST` | `/api/runs/{id}/complete` | 标记完成 |

创建请求体：
```json
{
  "user_request": "今天 AI 圈有什么值得写的？",
  "style_id": "caoz",
  "target_platform": "wechat",
  "config": {
    "research_parallel": 5,
    "max_revise_rounds": 2,
    "max_images": 3,
    "budget_limit_cents": 500
  }
}
```

SSE 事件格式：
```
event: agent.start
data: {"ts": 0.05, "agent": "topic"}

event: writer.token
data: {"ts": 4.52, "text": "这两天科技圈"}

event: image.generated
data: {"ts": 6.10, "para_id": 1, "url": "data/images/a8c2_1.png"}

event: graph.done
data: {"ts": 8.37, "status": "done", "words": 1872, "images": 3}
```

#### 6.6.2 Topics（选题）

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/topics/candidates` | 今日候选选题（调热榜聚合） |
| `POST` | `/api/topics/refresh` | 强制刷新 |

#### 6.6.3 Styles（风格）

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/styles` | 列表 |
| `GET` | `/api/styles/{id}` | 详情（含指纹数据） |
| `POST` | `/api/styles` | 新建 |
| `PUT` | `/api/styles/{id}` | 更新 |
| `DELETE` | `/api/styles/{id}` | 删除 |
| `POST` | `/api/styles/{id}/samples` | 上传范文 |
| `POST` | `/api/styles/{id}/analyze` | 触发指纹分析 |

#### 6.6.4 Stats + Settings

| 方法 | 路径 | 说明 |
|---|---|---|
| `GET` | `/api/stats/dashboard` | 今日产出/本月累计/平均成本/pass 率 |
| `GET` | `/api/settings` | 读取配置 |
| `PUT` | `/api/settings` | 更新配置 |

### 6.7 环境变量

```bash
# 必填
MIMO_API_KEY=tp-xxx              # 小米 MiMo API Key

# 可选
MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
MIMO_MODEL=MiMo-V2.5-Pro         # 主力模型
MIMO_MODEL_FAST=MiMo-V2.5        # 轻量模型
SILICONFLOW_API_KEY=sk-xxx       # 硅基流动（图像生成）
SILICONFLOW_IMAGE_MODEL=black-forest-labs/FLUX.1-schnell  # 默认图像模型
```

---

## 7. 风险与缓解

| 风险 | 概率 | 影响 | 缓解 |
|---|---|---|---|
| LLM 编造事实 | 高 | 高 | prompt 强制引用 snippet + Reviewer 校验 + 人工抽查 |
| 图文不一致 | 中 | 中 | Phase 1 文本层面校验；Phase 2 Vision 模型校验 |
| 风格学习样本不足 | 中 | 中 | 最低 5 篇样本要求 + UI 警告提示 |
| MiMo API 限流/不稳定 | 中 | 中 | tenacity 重试 + 环境变量切换 provider |
| 热榜 API 被反爬 | 中 | 低 | 多源冗余（6 源挂 1~2 个不影响）+ 请求间隔 |
| SiliconFlow 免费额度用完 | 低 | 低 | 降级为只输出图片 prompt 不生成 |
| 单次生成超时 | 中 | 中 | 每 agent 设超时 + 整体 15min 硬上限 |
| SQLite 并发写入冲突 | 低 | 低 | WAL 模式 + 单用户场景足够 |

---

## 8. 里程碑与验收

### 8.1 实施计划（3 周）

| 阶段 | 目标 | 关键交付 | 验收 |
|---|---|---|---|
| **W1 前半** | LLM + DB + Tools | `llm.py` 对接 MiMo；`db.py` 建表；`tools/` 集成热榜+风格 | `python -c "from app.llm import LLMClient"` 通过 |
| **W1 后半** | Agent 流水线 | `graph.py` 7 个 Agent 接真 LLM + 真工具 | `python -m app.agents.graph` 端到端生成 1 篇文章 |
| **W2 前半** | FastAPI 路由 | runs/topics/styles/stats/settings 全部路由 | `uvicorn app.main:app` 启动；curl 测试通过 |
| **W2 后半** | 图像生成 | `image_gen.py` 对接 SiliconFlow；IllustratorAgent 生成真实配图 | 端到端含配图生成通过 |
| **W3** | 前端 + 联调 | Vue 3 SPA 6 个页面；SSE 实时推送 | 浏览器 `localhost:8000` 全流程 demo |

### 8.2 验收标准（Phase 1 出口）

- [ ] 端到端 demo：输入一句话 → 8 分钟内拿到完整图文（含 2~3 张配图）
- [ ] 6 个前端页面可用
- [ ] 热榜聚合至少 3 源可用（百度 + 微博 + RSS）
- [ ] 风格指纹至少 1 个可用（可自建）
- [ ] 连续 10 次 run 成功率 ≥ 80%
- [ ] API 文档自动生成（FastAPI OpenAPI）
- [ ] `--mock` 模式零依赖可跑（演示/测试用）

### 8.3 依赖安装

```bash
pip install fastapi uvicorn openai aiosqlite
# aiosqlite 用于 FastAPI 异步 DB 操作
# openai 用于 MiMo + SiliconFlow（都是 OpenAI 兼容格式）
```

---

## 9. 附录

### 9.1 术语表

| 术语 | 含义 |
|---|---|
| **Run** | 一次完整的"输入 → 草稿"端到端流程 |
| **Snippet** | Researcher 抓回的素材片段（带来源、可信度） |
| **Style Fingerprint** | 风格指纹，由 style_fingerprint 分析出的 JSON（句长、反问率、高频词等） |
| **Outline** | 文章大纲，section 数组 |
| **Image Prompt** | 写手在草稿里留下的 `[IMG: 描述 | 比例]` 占位符 |
| **Review** | Reviewer 输出的 `{pass, score, issues}` 对象 |
| **AgentLLM** | 统一 LLM 接口，真 API 和 Mock 共用 |
| **SiliconFlow** | 硅基流动，国内 AI 模型云服务商，提供 FLUX/Seedream 图像生成 API |

### 9.2 数据契约示例

详见 `app/agents/graph.py` 中 `ContentState` dataclass。

### 9.3 失败恢复策略表

| 失败点 | 自动恢复 | 人工介入 |
|---|---|---|
| Topic 失败 | 重试 1 次（换温度） | 让用户手填 |
| Researcher 单 worker 失败 | 跳过，其他继续 | 不必 |
| Researcher 全部失败 | 降级到只用热榜标题 | 警告 |
| Image 生成失败 | 重试 2 次；降级为只保留 prompt 占位符 | 让用户手动上传 |
| Reviewer pass=false | Reviser 修订 ≤2 次 | 超出转 needs_human |
| 整体超时（> 15min） | abort + 保存中间状态 | 弹"从断点续跑 vs 重新开始" |
| MiMo API 报错 | tenacity 重试 3 次 | 提示用户检查 API Key |
| 热榜 API 被封 | 跳过该源，用其他源 | 不必 |

### 9.4 后续 Phase 预告

- **Phase 2**：PostgreSQL + pgvector 迁移；向量 RAG 去重；知乎/头条/抖音采集（Node.js 改写纯 Python）；发布矩阵（公众号 API + 浏览器自动化）；MiMo-V2-Omni 做图文 Vision 校验；Langfuse 可观测
- **Phase 3**：数据回流（阅读量、点赞）+ 自动 prompt 调优
- **Phase 4**：多账号矩阵 + 团队协作 + 移动端
