# PLAN4 — 可分步执行的端到端收口任务列表

> 日期：2026-05-11  
> 目标：把项目收口到“用户只通过前端操作，也能顺畅完成从创建任务到拿到草稿的全流程”，没有静默失败、假 loading、空白页面或断链。

---

## 0. 完成定义

只有同时满足下面 8 条，项目才算完整：

1. 用户在 Dashboard / NewRun 页面可以顺利创建任务。
2. 创建失败时，前端有明确错误提示，不会像“点了没反应”。
3. 任务启动后，RunLive 一定能显示事件、正文流式输出或失败原因三者之一。
4. WriterAgent 流式输出区不会长期停留在“等待 WriterAgent 输出...”。
5. 任务完成后，Dashboard 的“今日草稿”能看到草稿箱。
6. 点击草稿箱条目可以进入编辑器，并看到 `draft_md` / `final_md`。
7. 刷新页面后，历史事件和草稿仍然可回放。
8. 所有核心路径都有自动化测试和人工验收步骤。

---

## 1. 执行原则

- 每一阶段必须先验收，再进入下一阶段。
- 每个任务都要产出“代码改动 + 验收证据”。
- 优先修“前端无反馈”的问题，再补性能、统计和体验细节。
- 没有完成 P0 之前，不做额外功能扩展。

---

## 2. 阶段总览

| 阶段 | 目标 | 状态 | 通过标准 |
|---|---|---|---|
| Phase 1 | 固定运行环境 | `TODO` | 浏览器访问的就是当前后端，`/health` 正常 |
| Phase 2 | 打通创建任务链路 | `DONE` | 前端点击“启动生成”后，必有成功跳转或明确错误 |
| Phase 3 | 打通 RunLive 实时反馈 | `DONE` | 事件流、失败状态、Writer 输出三者至少有一项可见 |
| Phase 4 | 打通草稿回收链路 | `DONE` | Dashboard 草稿箱 → Editor 全通 |
| Phase 5 | 补齐统计与完整性 | `TODO` | token / 成本 / 事件回放可信 |
| Phase 6 | 自动化与验收封板 | `TODO` | 测试用例齐全，可重复执行 |

---

## 3. 可执行任务列表

### Phase 1：固定运行环境

#### T1-1 统一本地启动方式

- 状态：`TODO`
- 任务：
  - 清理旧的 `8000` 端口 Python 进程。
  - 固定启动顺序：Postgres → Alembic → Uvicorn。
  - 确认浏览器访问的是当前代码启动的服务。
- 相关文件：
  - `.env`
  - `docker-compose.yml`
  - `README.md`
- 验收：
  - `GET /health` 返回 `{"status":"ok"}`
  - `GET /api/runs?limit=1` 返回 JSON
  - 浏览器刷新后仍能打开首页

#### T1-2 补充启动自检说明

- 状态：`TODO`
- 任务：
  - 把“启动前检查项”写进文档。
  - 明确 Postgres、后端、前端构建产物的健康检查命令。
- 相关文件：
  - `README.md`
  - `docs/FRONTEND_BACKEND_E2E_TEST_PLAN.md`
- 验收：
  - 新人按文档可以完成启动，不需要口头补充

---

### Phase 2：打通创建任务链路

#### T2-1 保证 NewRun 点击有明确结果

- 状态：`DONE`
- 任务：
  - 点击“启动生成”时发出 `POST /api/runs`
  - API 失败时前端显示错误
- 相关文件：
  - `frontend/src/app/components/NewRun.tsx`
  - `frontend/src/lib/api.ts`
- 已完成结果：
  - API 非 2xx 会带出响应内容
  - NewRun 已显示错误框
- 验收：
  - 后端挂掉时，用户能直接看到错误文本
  - 不再出现“按钮转一圈然后什么都没有”

#### T2-2 创建 run 后立即验证 run 状态

- 状态：`DONE`
- 任务：
  - 创建 run 成功后，前端在跳转 RunLive 前做一次 `getRun(run_id)` 读取
  - 如果 run 已经失败，直接把失败原因带进 RunLive
- 相关文件：
  - `frontend/src/app/components/NewRun.tsx`
  - `frontend/src/app/App.tsx`
  - `frontend/src/app/components/RunLive.tsx`
- 验收：
  - 后台秒失败时，不会出现“先跳过去空白 loading 很久”
- 已完成结果：
  - NewRun 创建成功后立即 `getRun(run_id)`，并把快照带入 RunLive

#### T2-3 为 create_run 增加联调测试

- 状态：`DONE`
- 任务：
  - 补 API 测试，覆盖创建成功与创建后后台失败两种情况
- 相关文件：
  - `tests/api/test_runs.py`
  - 新增 `tests/api/test_runs_lifecycle.py`
- 验收：
  - `POST /api/runs` 的成功/失败路径都有断言
- 已完成结果：
  - 新增 `tests/api/test_runs_lifecycle.py` 覆盖 create → get_run 与失败可见性

---

### Phase 3：打通 RunLive 实时反馈

#### T3-1 保证失败状态前端可见

- 状态：`DONE`
- 任务：
  - 后台 `graph.error` 出现在 RunLive 顶部
  - Writer badge 失败时显示 `failed`
- 相关文件：
  - `frontend/src/app/components/RunLive.tsx`
  - `app/workers/runner.py`
- 已完成结果：
  - RunLive 已能显示 `graph.error`
- 验收：
  - 任何后端失败都不会只剩空白 streaming

#### T3-2 打通 WriterAgent 流式输出

- 状态：`DONE`
- 任务：
  - 确认 WriterAgent 真实 emit `writer.token` / `agent.token`
  - 确认 `EventSource` 收到 named event
  - 确认前端用历史事件 + 实时事件合成正文
- 相关文件：
  - `app/agents/writer.py`
  - `app/workers/runner.py`
  - `app/api/runs.py`
  - `frontend/src/lib/useSSE.ts`
  - `frontend/src/app/components/RunLive.tsx`
- 验收：
  - `GET /api/runs/{id}/events` 中包含 `writer.token`
  - RunLive 的“已生成 ~ N 字符”中 `N > 0`
  - 文本区不再长期显示“等待 WriterAgent 输出...”
- 已完成结果：
  - Writer streaming 与非 streaming fallback 都会 emit `writer.token`
  - RunLive 使用历史事件 + 实时事件合成正文

#### T3-3 给 RunLive 增加无事件超时提示

- 状态：`DONE`
- 任务：
  - 如果创建任务后若干秒内没有任何业务事件，前端显示“任务未成功启动，请检查后端连接”
- 相关文件：
  - `frontend/src/app/components/RunLive.tsx`
- 验收：
  - 出现“后端没真正启动”这类问题时，页面有可理解提示
- 已完成结果：
  - RunLive 8 秒内无业务事件且未终态时显示启动/连接提示

#### T3-4 为实时链路补自动化断言

- 状态：`DONE`
- 任务：
  - 增加测试覆盖：`graph.start`、`agent.start`、`writer.token`、`graph.done` / `graph.error`
- 相关文件：
  - 新增 `tests/api/test_run_event_visibility.py`
- 验收：
  - 事件序列至少能被自动化跑通一次
- 已完成结果：
  - 新增 `tests/api/test_run_event_visibility.py` 覆盖 `graph.start`、`agent.start`、`writer.token`、`graph.done`

---

### Phase 4：打通草稿回收链路

#### T4-1 Dashboard 今日草稿箱可用

- 状态：`DONE`
- 任务：
  - 点击“今日草稿”展开草稿箱
  - 草稿箱展示今日草稿列表
- 相关文件：
  - `frontend/src/app/components/Dashboard.tsx`
- 已完成结果：
  - 今日草稿箱已可展开
- 验收：
  - 用户能从 Dashboard 看到今天的草稿入口

#### T4-2 草稿箱 → 编辑器链路验收

- 状态：`DONE`
- 任务：
  - 确认点击草稿箱条目后进入 Editor
  - Editor 能展示 `draft_md` 或 `final_md`
  - 如果草稿为空，给出明确说明
- 相关文件：
  - `frontend/src/app/components/Dashboard.tsx`
  - `frontend/src/app/components/ArticleEditor.tsx`
  - `frontend/src/app/App.tsx`
- 验收：
  - 从 Dashboard 进入 Editor 不会卡死或只看到默认占位文本
- 已完成结果：
  - Dashboard 传 runId 到 Editor，Editor 读取 `final_md || draft_md`，空草稿/读取失败有明确说明

#### T4-3 完成后自动回流到草稿箱

- 状态：`DONE`
- 任务：
  - run 完成后确保 Dashboard 的列表刷新能看见该条 run
- 相关文件：
  - `frontend/src/app/components/Dashboard.tsx`
  - `app/api/stats.py`
  - `app/api/runs.py`
- 验收：
  - 完成一条任务后回 Dashboard，无需额外操作即可看到草稿
- 已完成结果：
  - run 完成时持久化 `draft_md` / `final_md` / token 汇总，返回 Dashboard 会刷新列表

---

### Phase 5：补齐统计与完整性

#### T5-1 run 级 token / cost 汇总可信

- 状态：`TODO`
- 任务：
  - 聚合 `token_usage` 到 `runs.total_tokens` / `runs.cost_cents`
  - 聚合 `usage_by_agent`
- 相关文件：
  - `app/llm/client.py`
  - `app/workers/runner.py`
  - `app/api/stats.py`
- 验收：
  - RunLive 的累计 token 不恒为 0
  - 成本饼图有真实数据

#### T5-2 事件回放可靠

- 状态：`TODO`
- 任务：
  - 刷新 RunLive 后，历史事件能继续显示
  - 事件读取顺序稳定
- 相关文件：
  - `app/api/runs.py`
  - `frontend/src/app/components/RunLive.tsx`
- 验收：
  - 刷新页面后能看到之前的 `graph.start` / `writer.token` / `graph.done`

#### T5-3 中止、继续、重试的前端行为收口

- 状态：`TODO`
- 任务：
  - 明确 `interrupt` / `resume` / `abort` 的真实行为
  - 页面按钮状态与后端状态一致
- 相关文件：
  - `app/api/runs.py`
  - `app/workers/runner.py`
  - `frontend/src/app/components/RunLive.tsx`
- 验收：
  - 点“中止”后任务不会继续跑
  - 点“继续”后不会只改状态不执行

---

### Phase 6：自动化与验收封板

#### T6-1 补 API 生命周期测试

- 状态：`TODO`
- 任务：
  - create → get_run → get_events → export 全链路覆盖
- 相关文件：
  - 新增 `tests/api/test_runs_lifecycle.py`
- 验收：
  - mock run 生命周期测试稳定通过

#### T6-2 补失败可见性测试

- 状态：`TODO`
- 任务：
  - 模拟 PG 不可达 / graph compile 失败
  - 断言 run 变 `failed` 且存在 `graph.error`
- 相关文件：
  - 新增 `tests/api/test_run_failure_visibility.py`
- 验收：
  - “静默失败”被测试阻断

#### T6-3 补前端集成测试

- 状态：`TODO`
- 任务：
  - 覆盖 NewRun 点击、RunLive 错误展示、今日草稿箱展开、草稿进入编辑器
- 相关文件：
  - `frontend` 测试目录
- 验收：
  - 至少 1 条前端自动化用例能跑通关键 happy path

#### T6-4 人工封板验收

- 状态：`TODO`
- 任务：
  - 用真实浏览器完整走一遍
- 验收清单：
  1. 打开 `http://127.0.0.1:8000/`
  2. 在前端输入“生成 AI 日报”
  3. 点击“启动生成”
  4. 页面出现 RunLive
  5. 页面出现事件、流式正文或明确失败
  6. 完成后回 Dashboard
  7. 点击“今日草稿”
  8. 打开草稿箱中的条目
  9. Editor 能显示草稿内容

---

## 4. 推荐执行顺序

按下面顺序推进，风险最低：

1. `T1-1` → `T1-2`
2. `T2-2` → `T2-3`
3. `T3-2` → `T3-3` → `T3-4`
4. `T4-2` → `T4-3`
5. `T5-1` → `T5-2` → `T5-3`
6. `T6-1` → `T6-2` → `T6-3` → `T6-4`

---

## 5. 每阶段最小验收命令

```bash
cd /Users/gongbenxi/Documents/aistudy/code/Skills_Repo-main/ai-content-factory
.venv/bin/pytest -q
cd frontend
npm run build
```

人工最小验收：

1. 打开首页。
2. 创建一条任务。
3. 确认不是“无反馈”。
4. 完成后从草稿箱进入编辑器。

---

## 6. 关联文档

- [docs/FRONTEND_BACKEND_E2E_TEST_PLAN.md](/Users/gongbenxi/Documents/aistudy/code/Skills_Repo-main/ai-content-factory/docs/FRONTEND_BACKEND_E2E_TEST_PLAN.md:1)
