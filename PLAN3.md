# PLAN3 — AI Content Factory 全面审计 & PRD 对齐修复计划

> 审计日期：2026-05-11
> 对照文档：`docs/PRD.md` Phase 1 v1.2
> 审计范围：PRD §1-§9 全部章节 × 前端 6 页 × 后端 API × Agent 流水线 × 画图流程
> 结论：Phase 1 骨架已搭，**但有 15 项 PRD 验收标准未达标**

---

## 〇、PRD 验收标准对照（§9.2）

| # | PRD 验收标准 | 当前状态 | 阻塞原因 |
|---|-------------|---------|---------|
| V-1 | 端到端 demo：8 分钟内拿到完整图文（含 2-3 张配图） | 🔴 FAIL | 画图流程 5 个阻断性 bug（§一） |
| V-2 | 6 个前端页面可用 | 🟡 PARTIAL | 20+ 按钮空壳（§二） |
| V-3 | 单篇成本 Token Plan 内趋近 ¥0 | 🔴 FAIL | Token/Cost 计量断路，始终返回 0（§三 B-1） |
| V-4 | 风格盲测识别率 < 70% | ⚠️ 未验 | WriterAgent 风格指纹注入用硬编码占位符（§三 B-10） |
| V-5 | 连续 50 次 run 成功率 ≥ 95% | ⚠️ 未验 | mock 通过，真 LLM 未压测 |
| V-6 | run_events 能回放任意一次 run | 🟡 PARTIAL | 6 种事件类型从未 emit（§三 B-11） |
| V-7 | Langfuse trace 可见 | ✅ PASS | |
| V-8 | 预算熔断验证（80% 降级 / 100% 熔断） | ✅ PASS | BudgetGuard 双模式已实现 |
| V-9 | 文档齐全（API 文档 + 部署文档） | 🔴 FAIL | 无部署文档，OpenAPI 自动生成但未整理 |

---

## 一、画图流程（🔴 PRD §4.7 全链路阻断）

PRD §4.7 定义了 7 步端到端图像生成流程。当前 **步骤②③⑤全部阻断**：

| # | PRD 步骤 | 问题 | 文件 | 根因 | P |
|---|---------|------|------|------|---|
| I-1 | ② Prompt 增强 | `enhance_prompt` 硬编码 `mock=True` | `image.py:62` | 无论 run 是否 mock，prompt 增强永远返回 mock 数据 | P0 |
| I-2 | ③ 缓存查询 | `image_cache.py` 无 DB fallback | `image_cache.py` | 无 PG → `get_cached_image()` / `save_to_cache()` 抛异常 → `generate_image()` 崩溃 | P0 |
| I-3 | ⑤ 下载落盘 | `_gen_ai_image` 不下载到本地 | `image.py:232-250` | PRD 要求"data/images/{run_id}_{para_id}.png"，实际 `local_path=""` | P0 |
| I-4 | ④→前端 | 无 `image.generated` SSE 事件 | `illustrator.py` | PRD §6.4 明确定义此事件，但从未 emit | P1 |
| I-5 | ④ 按 type 分发 | chart/infographic 依赖未安装 | `requirements.txt` | `pyecharts` / `playwright` 不在依赖 → 退化为灰色占位图 | P2 |
| I-6 | ④ AI 生图 | 无 API Key 时返回假 URL | `image.py:236-237` | 返回 `/data/images/{random}.png` 但文件不存在 | P1 |
| I-7 | ④ 备份链路 | 无 provider failover | `image.py` | PRD §4.7.1 要 FLUX→火山即梦→Coze 三级降级，当前只有一级 | P2 |
| I-8 | ⑦ 图文校验 | 无 `image_consistency_check` | `reviewer.py` | PRD §4.7.7 要求 Reviewer 逐图做图文一致性校验，当前仅全局 LLM 评审 | P2 |

### 修复方案

```python
# I-1: image.py enhance_prompt() 增加 mock 参数
async def enhance_prompt(placeholder: dict, style_id: str, mock: bool = False) -> str:
    content, _ = await llm.chat("illustrator", messages, mock=mock)  # 不再硬编码

# I-2: image_cache.py 加 try/except
async def get_cached_image(prompt_hash: str) -> dict | None:
    try:
        ...原有 SQL 逻辑...
    except Exception:
        return None  # 无 PG 跳过缓存

# I-3: _gen_ai_image 下载图片到本地
import httpx
async with httpx.AsyncClient() as client:
    resp = await client.get(url)
    local_path = DATA_DIR / filename
    local_path.write_bytes(resp.content)

# I-4: illustrator_agent 每张图 emit
await emit_event(run_id, "image.generated", {"para_id": ph["para_id"], "url": result["url"]})

# I-6: 无 Key 时用 Pillow 占位图
if not api_key:
    _gen_placeholder_image(local_path, prompt, ratio, "NO_API_KEY")
    return {"url": f"/data/images/{filename}", "local_path": local_path, "model": "placeholder"}
```

---

## 二、前端按钮/交互失效（🟡 PRD §4.14 / §3.1 多项不达标）

### 2.1 NewRun.tsx — PRD §4.14 "New Run" 页

| # | PRD 要求 | 按钮/控件 | 状态 | 说明 |
|---|---------|----------|------|------|
| F-1 | §6.4 CreateRun `config` 字段 | 并行度/修订轮次/配图数量/Token 预算 滑块 | ❌ | state 有值但 `createRun()` 不传 `config`（PRD 要求 `research_parallel`, `max_revise_rounds`, `max_images`, `budget_limit_cents`） |
| F-2 | §4.14 预估 | "预估" 卡片 | ❌ | "~ 6 分钟"、"~ 14 次" 硬编码，PRD 要根据参数动态算 |
| F-3 | §6.1 models.yaml | Agent 模型分配表 | ❌ | 静态数组，PRD 要从 `getSettings()` 读 |
| F-4 | §5.5 可观测 | "启用 Langfuse Trace" 开关 | ❌ | 无 onChange，不传后端 |
| F-5 | §3.1 M5 | "上传新风格..." 选项 | ❌ | 选 `custom` 无后续（PRD M5 要求可上传 URL 抽取指纹） |

### 2.2 RunLive.tsx — PRD §4.14 "Run Live" 页 / §3.1 M2

| # | PRD 要求 | 按钮/控件 | 状态 | 说明 |
|---|---------|----------|------|------|
| F-6 | §3.2 A3 Pause | "暂停" 按钮 | ⚠️ 伪 | 只改 DB status，**不暂停 LangGraph**（PRD A3 要求 `interrupt API`） |
| F-7 | §3.2 A3 Resume | "继续" 按钮 | ⚠️ 伪 | 同上 |
| F-8 | §6.4 abort | "中止" 按钮 | ⚠️ 伪 | 删 event queue 但 asyncio Task 继续跑 |
| F-9 | §3.1 M2 流式 | WriterAgent 流式输出 | ❌ | PRD §4.6 要求"流式输出，前端实时展示"，实际用 `llm.chat()` 一次性返回 |
| F-10 | §4.11 计量 | Per-Agent 成本饼图 | ❌ | `usage_by_agent` 全零（见 B-1） |

### 2.3 ArticleEditor.tsx — PRD §4.14 "Article Editor" 页 / §3.1 M3

| # | PRD 要求 | 按钮/控件 | 状态 | 说明 |
|---|---------|----------|------|------|
| F-11 | §4.14 富文本 | 工具栏 (Bold/Italic/Heading 等) | ❌ | PRD 要求 TipTap 富文本，当前 6 按钮全无 onClick |
| F-12 | §4.14 平台预览 | "公众号预览" tab | ⚠️ | `draft.slice(0,800)` 纯文本，PRD 要 Markdown→HTML 渲染 |
| F-13 | §3.1 M3 替换配图 | "批量重新生成" 按钮 | ❌ | 无 onClick（PRD M3 明确要求"替换配图"） |
| F-14 | §3.1 M3 替换配图 | 单张 "替换" 按钮 | ❌ | 无 onClick |
| F-15 | §3.1 M3 风格分数 | 风格匹配雷达图 | ❌ | `radarData` 硬编码，PRD M3 要求"看到风格匹配分数" |
| F-16 | §4.8 平台规范 | 平台合规检查 | ❌ | 所有数据写死，PRD §4.8 第 4 点要求实时检查 |

### 2.4 StyleManager.tsx — PRD §4.14 "Style Manager" 页 / §3.1 M5

| # | PRD 要求 | 按钮/控件 | 状态 | 说明 |
|---|---------|----------|------|------|
| F-20 | §3.1 M5 | "新增风格" 按钮 | ✅ | |
| F-21 | §3.1 M5 核心 | "抽取指纹" 按钮 | ❌ | PRD M5："上传公众号文章 URL，自动抽取风格指纹"—**无后端 API** |
| F-22 | §3.1 M5 | "批量上传" 按钮 | ❌ | 无 onClick |
| F-23 | §4.14 指纹可视化 | 风格卡片点击 | ❌ | `cursor-pointer` 无 onClick |
| F-24 | §4.14 词云 | 高频词分布图 | ❌ | `wordFreq` 硬编码 |
| F-25 | §4.14 句法图 | 句法特征面板 | ❌ | 全部写死 |

### 2.5 Settings.tsx — PRD §4.14 "Settings" 页 / §5.2

| # | PRD 要求 | 按钮/控件 | 状态 | 说明 |
|---|---------|----------|------|------|
| F-26 | §6.1 Provider 切换 | Provider 卡片 | ❌ | PRD："下拉切换 MiMo/DeepSeek/OpenAI"—无 onClick |
| F-27 | §5.2 Agent 分配 | Per-Agent 模型 Select | ❌ | 有 `value` 无 `onValueChange` |
| F-28 | §5.2 预算 | 预算滑块 | ❌ | `defaultValue` 非受控 |
| F-29 | §6.5 API Keys | API Key 输入框 | ❌ 只读 | PRD 要环境变量注入，Settings 页显示状态即可（保留 readOnly 合理） |
| F-30 | §5.5 可观测 | 高级开关 | ❌ | `defaultChecked` 非受控 |
| F-31 | §6.1 配置 | "保存设置" 按钮 | ⚠️ | 发送初始值（上游控件不更新 state） |

### 2.6 Sidebar + Dashboard

| # | PRD 要求 | 控件 | 状态 |
|---|---------|------|------|
| F-32 | §4.11 计量 | Sidebar Token 预算 | ❌ 硬编码 "43%" |
| F-33 | §4.14 KPI | 本周产出图表 | ⚠️ 仅今日 |

---

## 三、后端 / 数据流问题（🔴 多项 PRD 要求未实现）

| # | PRD 章节 | 问题 | 文件 | 说明 | P |
|---|---------|------|------|------|---|
| B-1 | §4.11 Token 计量 | **Token/Cost 计量断路** | 全部 agent | LLMClient 返回 usage 但 **无 agent** 把 `cost_cents` / `total_tokens` / `usage_by_agent` 写回 ContentState → 前端成本 KPI 永远 0 | P0 |
| B-2 | §6.4 SSE | SSE named event 格式待验证 | `runs.py:148` | yield `{"event": ..., "data": ...}` 需确认 sse-starlette 3.x 正确转换为 `event:` 行 | P1 |
| B-3 | §4.12 Schema | `session.get(Run, run_id)` 传 str | `runs.py` 多处 | Run.id 是 `UUID(as_uuid=True)`, 需 `uuid.UUID(run_id)` | P1 |
| B-4 | §3.2 A3 | interrupt/resume/abort 无真实控制 | `runs.py` | PRD A3 要求 "LangGraph interrupt API + 前端 state 编辑面板"，当前只改 DB 字段 | P1 |
| B-5 | §3.2 A1 | `retry_from_agent` 是空壳 | `runs.py:307` | PRD A1 要求 "LangGraph checkpoint + Retry from XXX 按钮"，当前只改 status | P2 |
| B-6 | §6.1 配置 | Settings PUT 无验证 | `settings.py` | 覆盖写 models.yaml 无 schema 验证，畸形数据击溃 LLM | P1 |
| B-7 | §4.14 Dashboard | stats/dashboard 无内存计算 | `stats.py` | 无 PG 返回全零，应从 RUNS 计算 | P2 |
| B-8 | §6.4 topics/refresh | `/api/topics/refresh` 空壳 | `topics.py:22` | 返回 `{"refreshed": True}` 不做事 | P3 |
| B-9 | §4.6 流式 | WriterAgent 非流式 | `writer.py` | PRD："流式输出，前端实时展示"，实际用 `llm.chat()` | P1 |
| B-10 | §4.5/§4.6 风格注入 | 风格指纹占位硬编码 | `writer.py` / `editor.py` | PRD §4.5 要求 `load_style_fingerprint` 加载指纹 JSON，WriterAgent 注入句法/高频词/修辞。当前用 `"短句为主"` 等硬编码字符串 | P1 |
| B-11 | §6.4 事件类型 | 6 种 SSE 事件从未 emit | 全部 agent | PRD 定义的 `agent.token` / `tool.call` / `image.generated` / `review.done` / `budget.warning` / `writer.token` 均无实现 | P1 |
| B-12 | §4.11.3 成本计算 | 无 MODEL_PRICING / calc_cost | `llm/` | PRD §4.11.3 定义了 per-model 定价表和 `calc_cost()`，LLMClient 里 `cost_cents` 始终为 0 | P1 |
| B-13 | §5.1 硬超时 | 无 15 分钟硬超时 | `runner.py` | PRD §5.1："单 run 硬超时 15 分钟" — 当前无超时机制 | P2 |
| B-14 | §6.4 CreateRun | CreateRun 缺 `config` 字段 | `runs.py` | PRD 要求 `config: {research_parallel, max_revise_rounds, max_images, budget_limit_cents}` | P1 |
| B-15 | §4.9 needs_human | revise 超限后无 `needs_human` 状态 | `graph.py:review_gate` | PRD §4.9："超出 → 状态 needs_human"，当前直接 → END | P2 |

---

## 四、PRD 功能缺失（❌ Phase 1 In Scope 但未实现）

| # | PRD 章节 | 缺失功能 | 说明 | P |
|---|---------|---------|------|---|
| M-1 | §4.2 TopicAgent | `vector_search_history` | PRD 要求用 pgvector 排除最近 30 天写过的选题，当前无实现 | P2 |
| M-2 | §4.4 Researcher | `vector_search_history` | PRD 要求每个 worker 调用看历史素材可复用的，当前无实现 | P2 |
| M-3 | §4.5 Editor | `load_style_fingerprint` | PRD 要求加载风格指纹 JSON 做大纲调整，当前只传 style_id 字符串 | P1 |
| M-4 | §4.12 Schema | `snippets` 表跨 run 复用 | PRD §4.12.2 定义了 snippets 表做素材去重复用，当前 snippets 只在 state 中 | P3 |
| M-5 | §4.12 Schema | `style_samples` 表 | PRD 定义了风格样本范文表，当前无使用 | P3 |
| M-6 | §4.12 RAG | BGE-M3 embedding + pgvector 检索 | PRD §4.12.3 定义了 L1 新鲜素材 + L2 历史避重双层检索，完全未实现 | P3 |
| M-7 | §4.7.7 | 图文一致性逐图校验 | PRD 要求 Reviewer 对每张图做 description vs paragraph 匹配判定，当前仅全局评审 | P2 |
| M-8 | §4.7.8 | Reviser 图文不匹配双策略 | PRD 定义"优先改文，次之重生图"双策略，Reviser 当前不处理 image_mismatch | P2 |
| M-9 | §6.4 | `POST /api/styles/{id}/analyze` | PRD API 清单中有，当前未实现 | P1 |
| M-10 | §4.14 Editor | TipTap 富文本编辑器 | PRD 要求 TipTap，当前用 Textarea | P2 |
| M-11 | §5.3 | `app/config.py` Pydantic Settings | PRD §6.3 要求从 models.yaml + 环境变量读取的配置类 | P3 |
| M-12 | §6.3 | `app/tools/rag.py` pgvector 检索 | PRD 文件结构列出但未创建 | P3 |
| M-13 | §6.3 | `app/observability/metrics.py` Prometheus | PRD 文件结构列出但未创建 | P3 |
| M-14 | §9.2 | 部署文档 | PRD 验收标准要求但不存在 | P2 |

---

## 五、修复路线图（按 PRD 验收标准倒排）

### Phase 3.1 — 阻断性修复（2 天）

> 🎯 目标：V-1 端到端 demo 跑通 + V-3 成本计量闭环

| 序号 | 任务 | 关联 | 文件 |
|-----|------|------|------|
| 1 | 修 `enhance_prompt` mock 参数传递 | I-1 | `image.py`, `illustrator.py` |
| 2 | `image_cache.py` 加 DB fallback（try/except） | I-2 | `image_cache.py` |
| 3 | `_gen_ai_image` 下载图片到 `data/images/` | I-3 | `image.py` |
| 4 | 无 SILICONFLOW_API_KEY 时生成 Pillow 占位图 | I-6 | `image.py` |
| 5 | 实现 `MODEL_PRICING` + `calc_cost()` | B-12 | `app/llm/pricing.py`（新建） |
| 6 | 每个 Agent 返回 usage 累加到 ContentState | B-1 | 全部 8 个 agent |
| 7 | 修 `session.get(Run, uuid.UUID(run_id))` | B-3 | `runs.py` |
| 8 | `illustrator_agent` emit `image.generated` 事件 | I-4 | `illustrator.py` |
| 9 | `CreateRunRequest` 增加 `config` 字段 | B-14, F-1 | `runs.py`, `runner.py` |

### Phase 3.2 — SSE + 流式输出（1.5 天）

> 🎯 目标：V-6 事件回放完整 + M2 实时进度达标

| 序号 | 任务 | 关联 | 文件 |
|-----|------|------|------|
| 10 | WriterAgent 改 `llm.stream()` + emit `agent.token` | B-9, F-9 | `writer.py` |
| 11 | 所有 agent 的 `tool.call` 事件 emit | B-11 | `researcher.py`, `reviewer.py` |
| 12 | ReviewerAgent emit `review.done` 事件 | B-11 | `reviewer.py` |
| 13 | BudgetGuard emit `budget.warning` 事件 | B-11 | `budget.py`, `client.py` |
| 14 | 验证/修复 SSE named event 格式（sse-starlette） | B-2 | `runs.py` |
| 15 | run 15 分钟硬超时 | B-13 | `runner.py` |

### Phase 3.3 — 风格系统补全（1.5 天）

> 🎯 目标：V-4 风格盲测 + M5 抽取指纹达标

| 序号 | 任务 | 关联 | 文件 |
|-----|------|------|------|
| 16 | 新增 `POST /api/styles/{id}/analyze` endpoint | M-9, F-21 | `styles.py` |
| 17 | StyleManager "抽取指纹" 按钮接通 | F-21 | `StyleManager.tsx` |
| 18 | StyleManager URL 输入框改受控 + "批量上传" 接通 | F-22 | `StyleManager.tsx` |
| 19 | Editor/Writer 加载真实风格指纹 `style.fingerprint` | B-10, M-3 | `editor.py`, `writer.py`, `styles.py` |
| 20 | 风格卡片点击展示详情（指纹 JSON → 图表） | F-23~F-25 | `StyleManager.tsx` |
| 21 | ArticleEditor 雷达图从 `run.review` 动态生成 | F-15 | `ArticleEditor.tsx` |

### Phase 3.4 — 前端全面接通（2 天）

> 🎯 目标：V-2 全部 6 页可用

| 序号 | 任务 | 关联 | 文件 |
|-----|------|------|------|
| 22 | 编辑器工具栏接通（Markdown 语法插入） | F-11 | `ArticleEditor.tsx` |
| 23 | 公众号预览改 `react-markdown` 渲染 | F-12 | `ArticleEditor.tsx`, `package.json` |
| 24 | 平台合规检查从 draft 实时分析 | F-16 | `ArticleEditor.tsx` |
| 25 | Settings Provider/Agent/Budget 改受控组件 + 保存 | F-26~F-31 | `Settings.tsx` |
| 26 | Settings PUT 加 schema 验证 | B-6 | `settings.py` |
| 27 | Sidebar Token 预算从 API 实时取 | F-32 | `Sidebar.tsx`, `App.tsx`, `stats.py` |
| 28 | NewRun 预估卡动态计算 + Agent 模型从 API 读 | F-2, F-3 | `NewRun.tsx` |
| 29 | stats/dashboard 无 PG 时从 RUNS 计算 | B-7 | `stats.py` |
| 30 | 本周产出统计（新增 `/api/stats/weekly`） | F-33 | `stats.py`, `Dashboard.tsx` |

### Phase 3.5 — 后端加固（1.5 天）

> 🎯 目标：A1/A3 异常路径 + V-5 稳定性

| 序号 | 任务 | 关联 | 文件 |
|-----|------|------|------|
| 31 | 实现真实 abort（保存 asyncio.Task + cancel） | B-4, F-8 | `runner.py`, `runs.py` |
| 32 | revise_count ≥ 2 时设 status=`needs_human` | B-15 | `graph.py:review_gate` |
| 33 | `/api/topics/refresh` 真实刷新 | B-8 | `topics.py` |
| 34 | 配图重新生成 API + 前端接通 | F-13, F-14 | `runs.py`, `image.py`, `ArticleEditor.tsx` |
| 35 | NewRun "上传新风格" 流程（弹窗→粘贴/URL→extract） | F-5 | `NewRun.tsx` |
| 36 | image provider failover 链 | I-7 | `image.py` |

### Phase 3.6 — 文档 & 验收（0.5 天）

> 🎯 目标：V-9 文档齐全

| 序号 | 任务 | 关联 | 文件 |
|-----|------|------|------|
| 37 | 部署文档（Docker Compose + env 配置） | M-14 | `docs/DEPLOY.md` |
| 38 | OpenAPI 文档整理 + README 更新 | V-9 | `README.md` |

### Phase 3.7 — Phase 2 预留（暂不实施，PRD 标注 Phase 2）

| 任务 | PRD 章节 | 说明 |
|------|---------|------|
| RAG 双层检索 (BGE-M3 + pgvector) | §4.12.3 | 需部署 BGE-M3 embedding 模型 |
| snippets 跨 run 复用 | §4.12.2 | 依赖 RAG 层 |
| style_samples 范文表 | §4.12.2 | 依赖 embedding |
| Vision 图文校验 (GLM-4V / Qwen-VL) | §4.7.7 | Phase 2 升级 |
| Reviser 图文双策略 | §4.7.8 | 依赖 Vision 校验 |
| TipTap 富文本编辑器 | §4.14 | 当前 Textarea 可用，TipTap 体验优化 |
| LangGraph interrupt + Command(resume=) | §3.2 A3 | 需要 checkpoint 完整支持 |
| retry_from_agent 真实重跑 | §3.2 A1 | 需要 checkpoint + subgraph |
| Prometheus 指标 | §5.5 | Phase 2 |
| 阿里云内容安全 API | §5.4 | Phase 2 |

---

## 六、文件变更清单

### 后端修改

| 文件 | 变更 | 关联任务 |
|------|------|---------|
| `app/tools/image.py` | mock 传参 + 下载落盘 + 占位图 + failover | 1, 3, 4, 36 |
| `app/tools/image_cache.py` | DB fallback | 2 |
| `app/agents/illustrator.py` | mock 传透 + image.generated 事件 | 1, 8 |
| `app/agents/writer.py` | 改流式 + agent.token 事件 + 风格注入 | 10, 19 |
| `app/agents/topic.py` | usage 写回 state | 6 |
| `app/agents/planner.py` | usage 写回 state | 6 |
| `app/agents/editor.py` | usage 写回 + load fingerprint | 6, 19 |
| `app/agents/researcher.py` | usage 写回 + tool.call 事件 | 6, 11 |
| `app/agents/reviewer.py` | usage 写回 + review.done 事件 + tool.call | 6, 12, 11 |
| `app/agents/reviser.py` | usage 写回 | 6 |
| `app/agents/graph.py` | review_gate → needs_human | 32 |
| `app/api/runs.py` | UUID 修复 + config 字段 + 配图重生 API | 7, 9, 34 |
| `app/api/styles.py` | analyze endpoint + fingerprint 返回 | 16 |
| `app/api/settings.py` | schema 验证 | 26 |
| `app/api/stats.py` | 内存计算 + weekly API | 29, 30 |
| `app/api/topics.py` | 真实 refresh | 33 |
| `app/llm/pricing.py` | 新建：MODEL_PRICING + calc_cost | 5 |
| `app/llm/client.py` | 调 calc_cost 填充 cost_cents | 5 |
| `app/llm/budget.py` | emit budget.warning 事件 | 13 |
| `app/workers/runner.py` | Task 引用 + cancel + 15 分钟超时 | 15, 31 |

### 前端修改

| 文件 | 变更 | 关联任务 |
|------|------|---------|
| `NewRun.tsx` | config 传参 + 预估动态 + Agent 模型读 API + 上传风格 | 9, 28, 35 |
| `RunLive.tsx` | 流式拼接修复 | 10 |
| `ArticleEditor.tsx` | 工具栏 + react-markdown + 雷达图 + 合规 + 配图替换 | 22-24, 21, 34 |
| `StyleManager.tsx` | 抽取指纹 + 批量上传 + 卡片详情 + 动态数据 | 17-18, 20 |
| `Settings.tsx` | 受控组件全面改造 | 25 |
| `Sidebar.tsx` | Token 预算实时 | 27 |
| `Dashboard.tsx` | 本周统计 | 30 |
| `package.json` | + react-markdown | 23 |

---

## 七、已确认正常（PRD 达标）

| PRD 要求 | 实现 |
|---------|------|
| §4.1 8 Agent 协同 LangGraph | ✅ StateGraph + 8 node + Send fan-out + review_gate |
| §4.10 ContentState TypedDict | ✅ 字段完全匹配 PRD |
| §4.2 百度热搜采集 | ✅ `hotnews.py` 正确解析 API |
| §6.1 多 Provider 路由 | ✅ models.yaml → resolve_model → AsyncOpenAI |
| §4.11.4 BudgetGuard 双模式 | ✅ token 模式 + 金额模式 |
| §5.5 Langfuse trace | ✅ _trace_to_langfuse 每次 LLM 调用上报 |
| §6.1 models.yaml 配置 | ✅ 3 provider + 8 agent + budget |
| §4.8 自建敏感词 | ✅ `safety.py` + 默认关键词表 |
| §4.4 web_search + scraper | ✅ Tavily + Crawl4AI（mock fallback） |
| §4.12 内存 fallback | ✅ memory_store.py (RUNS/EVENTS/STYLES) |
| §4.14 Dashboard KPI | ✅ getDashboard + getCandidates + listRuns |
| §6.4 runs CRUD + SSE | ✅ 全部 endpoint 存在 |
| §3.1 M4 导出 markdown | ✅ exportRun + completeRun |
| §4.7.5 倒序替换占位符 | ✅ render_with_images 正确实现 |
| §4.7.3 占位符解析 + 上下文 | ✅ parse_placeholders 带 ±400 字 |

---

## 总结

| 类别 | 数量 | Phase |
|------|------|-------|
| 🔴 P0 阻断（画图+计量+UUID） | 9 项 | 3.1 |
| 🟡 P1 核心功能缺失 | 15 项 | 3.2-3.4 |
| ⚠️ P2 应有功能 | 12 项 | 3.4-3.5 |
| 📋 P3 Phase 2 预留 | 10 项 | 暂不实施 |
| ✅ 已达标 | 15 项 | — |

**Phase 3.1-3.6 预计总工时：9 天**
- 3.1 阻断性修复：2 天
- 3.2 SSE + 流式：1.5 天
- 3.3 风格系统：1.5 天
- 3.4 前端全面接通：2 天
- 3.5 后端加固：1.5 天
- 3.6 文档验收：0.5 天

**修复后预期 PRD 验收达标率：V-1 ~ V-9 全部 PASS**（V-4 风格盲测需人工验证）
