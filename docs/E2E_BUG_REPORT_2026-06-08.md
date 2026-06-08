# 前后端数据库端到端点击测试 Bug 汇总

测试时间：2026-06-08 21:35-21:50（Asia/Shanghai）

测试目标：使用浏览器点击主要前端按钮，串联验证前端、后端 API、PostgreSQL 数据库是否端到端跑通。本轮只收集问题，不做业务修复。

## 测试环境

- 前端地址：http://127.0.0.1:8000/
- 后端服务：Uvicorn / FastAPI
- 数据库容器：`acf-postgres`
- 当前前端 bundle：`index-C7Ko3kHs.js`
- 当前 Provider：DeepSeek
- 浏览器工具限制：本轮 in-app browser 的自动输入/粘贴能力会被虚拟剪贴板拦截，因此“需要输入文字”的用例主要通过按钮点击 + API/DB 交叉验证完成。

## 覆盖范围

已点击/验证：

- 左侧导航：仪表盘、新建运行、实时运行、文章编辑器、风格管理、设置、明暗切换
- 仪表盘：刷新、刷新热榜、开始新一轮生成、查看最新
- 新建运行：启动生成
- 实时运行：暂停、继续、中止、打开编辑器入口
- 事件流：点击事件行可展示事件数据
- 文章编辑器：预览 Tab、工具栏、导出、保存、标记完成、返回
- 风格管理：新增风格、粘贴、抽取指纹、风格卡片
- 设置：Tab 切换、保存设置、恢复默认
- 后端接口：`/api/runs`、`/api/runs/{id}/events`、`/api/topics/refresh`、`/api/styles/{id}/analyze`、`/api/runs/{id}/regenerate-image`
- 数据库：`runs`、`run_events`、`styles`、`style_samples`、`token_usage`、`image_cache`

## 关键结论

当前“真实 run”没有完整打通数据库闭环。前端默认风格 `caoz` 不存在于数据库 `styles` 表，而 `runs.style_id` 有外键约束，导致创建真实 run 时数据库写入失败，后端静默 fallback 到 memory。前端看起来运行了，但 DB 里没有该 run，也没有事件持久化。

## Bug 列表

### P0-1 新建真实 run 未落库，后端静默 fallback 到 memory

现象：

- 在前端点击“新建运行” → “启动生成”，创建 run `875ed591-a74a-4879-bb16-452c92731ed0`。
- 页面进入实时运行，能看到 `graph.start`、`agent.start`。
- API 能读取该 run，但事件接口返回 `_source: "memory"`。
- PostgreSQL `runs` 表中查不到该 run。

证据：

```text
GET /api/runs/875ed591-a74a-4879-bb16-452c92731ed0/events?after_id=0
=> {"events":[...], "run_id":"875ed591...", "_source":"memory"}

SELECT id FROM runs WHERE id='875ed591-a74a-4879-bb16-452c92731ed0';
=> 0 rows
```

根因判断：

- 前端默认 style 是 `caoz`。
- DB `styles` 表当前只有：

```text
20c3d43e  你好
e3d94c57  你好
```

- `runs.style_id` 有外键：`FOREIGN KEY (style_id) REFERENCES styles(id)`。
- 创建 run 时插入 `style_id='caoz'` 失败，`create_run` 捕获异常后仅 debug log，并写入 memory。

影响：

- 真实运行无法进入数据库。
- 刷新/重启后 run 和事件可能丢失。
- “实时运行记录、文章记录、事件记录”与数据库不一致。

建议测试用例：

- `POST /api/runs` 使用不存在的 `style_id` 应返回 4xx，而不是 200 + memory fallback。
- 前端默认 style 必须来自 `/api/styles` 的真实 id。
- 创建 run 后断言 `runs`、`run_events` 都有记录。

### P0-2 LLM 余额不足导致风格分析和图片重生成 500，未结构化返回

现象：

- `POST /api/styles/{id}/analyze` 返回 `500 Internal Server Error`。
- `POST /api/runs/{id}/regenerate-image` 返回 `500 Internal Server Error`。
- 服务端日志显示 DeepSeek/OpenAI-compatible API 返回：

```text
Error code: 402 - Insufficient Balance
tenacity.RetryError[... APIStatusError]
```

影响：

- 前端无法给用户明确提示“余额不足/Key 不可用”。
- 重试消耗时间，最终只是泛化失败。
- 真实 E2E 在 LLM 余额不足时不可用。

建议测试用例：

- mock LLM 402，断言 API 返回结构化 402/503 JSON，而不是 500 text。
- 前端展示 provider、model、错误原因。
- 设置页提供 Provider/Key 预检。

### P1-1 中止 run 后自动跳转文章编辑器

现象：

- 在实时运行页点击“中止”。
- 后端状态变为 `aborted`。
- 前端立即进入文章编辑器，显示“运行未完成（aborted）”占位草稿。

证据：

```text
frontend/src/app/components/RunLive.tsx
handleAbort:
  await abortRun(runId);
  onDone();
```

影响：

- 用户点击中止的预期是停留在运行页看到终止状态。
- 自动进入编辑器容易误导用户以为有文章可编辑。

建议测试用例：

- 点击中止后页面仍停留在实时运行页。
- pipeline 节点显示 aborted。
- 编辑器入口仅在有真实草稿时高亮。

### P1-2 设置保存会重写 `config/models.yaml`，丢失注释和顺序

现象：

- 点击设置页“保存设置”，即使没有改变值，也会把 `config/models.yaml` 重新 dump。
- 注释丢失、provider/agent 顺序重排、行内格式被改写。

影响：

- 配置文件可读性下降。
- Git diff 噪音很大。
- “只点保存”会产生不必要代码变更。

建议测试用例：

- 未修改设置时保存，不应产生文件 diff。
- 保存只改动用户实际变更字段。
- 或迁移到数据库 settings 表，并保留配置模板只读。

### P1-3 API Keys 页显示硬编码状态，与真实 provider 不一致

现象：

- 当前系统 active provider 是 DeepSeek。
- 设置页 API Keys 显示 `DEEPSEEK_API_KEY` 未配置。
- 同时硬编码显示 `MIMO_API_KEY`、`COZE_API_KEY`、`TAVILY_API_KEY` 等已连接。

影响：

- 用户无法判断真实 Key 是否可用。
- 与 P0-2 的余额/Key 问题叠加，会误导排障方向。

建议测试用例：

- API Keys 页状态来自后端检测结果，而不是前端硬编码。
- active provider 的 key 缺失/余额不足必须显示高优先级告警。

### P1-4 后端导出为空，前端导出兜底为本地占位草稿，数据不一致

现象：

- 对 aborted run 调用 `/api/runs/{id}/export` 返回空内容。
- 前端点击“导出 .md”时会使用当前前端 draft 兜底，因此可能导出“运行未完成”占位文档。
- 如果用户点击编辑器工具栏，前端 draft 被本地修改，导出内容还会包含这些未保存修改。

影响：

- 导出内容不一定是后端真实文章。
- 可能把占位/未完成内容误当成正式稿导出。

建议测试用例：

- 无真实草稿时导出按钮应禁用或返回结构化错误。
- 导出内容必须来自后端已保存 draft/final。

### P1-5 文章编辑器工具栏在无真实草稿/预览页仍可修改占位内容

现象：

- aborted run 的保存/标记完成按钮禁用。
- 但标题、粗体、斜体、引用、链接、图片工具栏仍可点。
- 在“公众号预览”Tab 下点击工具栏也会修改本地 draft。

影响：

- 用户能编辑不可保存的占位草稿。
- 预览状态下工具栏行为不符合预期。

建议测试用例：

- `hasRealDraft=false` 时工具栏禁用。
- 预览 Tab 下工具栏禁用或自动切回编辑 Tab。

### P2-1 风格管理空操作缺少可见反馈

现象：

- 不填名称点击“新增风格”，无任何提示。
- 剪贴板不可用时点击“粘贴”，无任何提示。
- URL 为空时“抽取指纹”禁用是合理的，但应给出 tooltip 或说明。

影响：

- 用户会以为按钮不可用或点击无效。

建议测试用例：

- 空名称新增应显示错误提示。
- 剪贴板读取失败应显示“请手动粘贴 URL”。

### P2-2 设置页 Provider 卡片使用可点击 div，不利于自动化和无障碍

现象：

- Provider 选择区域是 clickable `div`，不是 button/radio。
- 自动化 DOM 中不可直接按按钮语义定位。

影响：

- 键盘访问、读屏、E2E 自动化稳定性较差。

建议测试用例：

- Provider 选项应具备 button/radio role。
- 键盘可切换 provider。

### P2-3 仪表盘初始数据短暂显示 0，刷新后变为真实数量

现象：

- 初始进入仪表盘时看到“今日草稿 0”。
- 点击刷新后变为“今日草稿 8”。

影响：

- 加载状态和真实空状态混淆。

建议测试用例：

- 数据加载中显示 skeleton/loading，不显示 0。
- 刷新后统计值与 `/api/stats/dashboard` 一致。

### P2-4 历史 mock/drafting 测试数据污染真实列表

现象：

数据库当前存在多个 `mock=true` 且长期 `drafting` 的 run：

```text
3a143863... drafting {"mock": true}
faf21191... drafting {"mock": true}
6125d458... drafting {"mock": true}
680617cd... drafting {"mock": true}
```

影响：

- 仪表盘和实时运行会优先打开这些假运行。
- 用户看到“生成中”但没有实际事件。

建议测试用例：

- mock run 完成后必须进入 done/failed/aborted 终态。
- Dashboard 可以过滤/标记 mock run。
- 长时间无事件的 drafting run 应有超时状态。

## 已确认跑通的链路

- 热榜刷新：`/api/topics/refresh` 返回 `refreshed=true`，`refresh_id` 从 2 变为 3，`source_counts={"baidu":30,"rss":30}`。
- 实时运行 SSE/事件展示：真实 run 创建后页面收到 `graph.start`、`agent.start`。
- 中止 API：`POST /api/runs/{id}/abort` 能把 memory run 置为 `aborted`。
- 文章编辑器路由：从运行页和仪表盘可进入。
- 设置 API：`GET /api/settings`、`PUT /api/settings` 可调用。

## 建议优先级

1. 修复 P0-1：禁止 DB 写失败静默 fallback；前端默认 style 必须来自数据库。
2. 修复 P0-2：统一 LLM/图片/风格分析错误结构，处理余额不足。
3. 修复 P1-1：中止后停留在运行页。
4. 修复 P1-2/P1-3：设置页持久化与 Key 状态真实化。
5. 清理历史 mock/drafting 数据或增加标识过滤。

## 建议沉淀的自动化测试

- `test_create_run_requires_valid_style_id`
- `test_create_run_persists_run_and_graph_start_event_to_db`
- `test_abort_does_not_navigate_to_editor`
- `test_llm_402_returns_structured_error`
- `test_settings_save_without_changes_has_no_diff`
- `test_export_disabled_when_no_real_draft`
- `test_dashboard_stats_loading_does_not_show_false_zero`
- `test_mock_run_reaches_terminal_state`

