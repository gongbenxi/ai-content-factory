# Frontend ↔ Backend 打通计划与测试用例

> 日期：2026-05-11  
> 背景：浏览器里下发“生成 AI 日报”后没有明显效果，需要把前端点击、API 创建、后台 LangGraph、SSE、草稿回读全链路打通。

## 1. 当前排查结论

| 位置 | 当前发现 | 影响 |
|---|---|---|
| 前端 NewRun | `启动生成` 会调用 `POST /api/runs` | 点击路径存在 |
| 前端错误展示 | 原本 `createRun` 失败只会结束 loading，没有错误提示 | 用户感觉“点了没用” |
| 后端 create_run | API 会先返回 `run_id`，后台再执行 LangGraph | 后台失败时前端可能已经跳到 RunLive |
| 后台任务 | `acompile_graph()` 或 PostgreSQL 连接失败会导致任务失败 | 必须在 RunLive 显示 `graph.error` |
| 当前运行态 | 8000 端口有 Python 进程，但本地 health 请求不可达 | 需要先标准化启动方式 |

已做改动：

- `frontend/src/lib/api.ts`：API 非 2xx 时携带响应正文，便于定位。
- `frontend/src/app/components/NewRun.tsx`：创建 run 失败时显示错误框。
- `frontend/src/app/components/RunLive.tsx`：后台 `graph.error` 会在页面顶部显示，Writer badge 会显示 `failed`。

## 2. 打通计划

### P0. 固定本地运行态

目标：保证浏览器访问的就是当前代码启动的后端，而不是旧进程或缓存页面。

执行步骤：

1. 停掉旧的 8000 Python 进程。
2. 启动 Docker Desktop PostgreSQL。
3. 执行 Alembic migration。
4. 用当前目录启动 `uvicorn app.main:app --host 127.0.0.1 --port 8000`。
5. 打开浏览器 `http://127.0.0.1:8000/health` 验证。

验收：

- `/health` 返回 `{"status":"ok"}`。
- `/api/runs?limit=1` 返回 JSON。
- 前端刷新后加载最新构建产物。

### P0. 打通创建任务

目标：点击“启动生成”后必须得到明确结果。

验收：

- 成功时跳转 RunLive，标题显示 `Run #xxxx`。
- 失败时停留 NewRun 并显示错误框。
- 后端日志不能只有静默 print，页面必须能看到失败原因。

### P0. 打通后台状态

目标：后台任务失败或成功都能反映到页面。

验收：

- 成功：RunLive 显示 `graph.start`、agent 事件、`graph.done`。
- 失败：RunLive 显示 `graph.error`，状态为 `failed`。
- 不能出现 `drafting + 0 事件 + 永远 streaming`。

### P0. 打通 Writer 流式输出

目标：WriterAgent 输出时页面实时出现正文。

验收：

- `/api/runs/{id}/events` 包含 `writer.token`。
- SSE 实时收到 `writer.token` 或 `agent.token`。
- RunLive 文本区不再停留“等待 WriterAgent 输出...”。
- `已生成 ~ N 字符` 中 `N > 0`。

### P1. 打通草稿箱和编辑器

目标：生成完成后能从 Dashboard 今日草稿进入编辑器。

验收：

- 点击“今日草稿”展开“今日草稿箱”。
- 草稿箱列表显示今日 run。
- 点击条目打开 ArticleEditor。
- Editor 能展示 `draft_md` 或 `final_md`。

## 3. 测试用例

### API 层

| ID | 用例 | 步骤 | 期望 |
|---|---|---|---|
| API-01 | 健康检查 | `GET /health` | 200, `status=ok` |
| API-02 | 创建 mock run | `POST /api/runs {"mock": true}` | 200, 返回 `run_id` |
| API-03 | 查询 run | `GET /api/runs/{id}` | 返回 `status`、`user_request` |
| API-04 | 查询事件 | `GET /api/runs/{id}/events` | 至少能返回数组 |
| API-05 | 后台失败可见 | 断开 PG 后创建 run | run 变 `failed`，事件包含 `graph.error` |
| API-06 | 导出草稿 | done run 调 `GET /api/runs/{id}/export` | 返回 markdown 文本 |

### 前端集成层

| ID | 用例 | 步骤 | 期望 |
|---|---|---|---|
| FE-01 | 新建任务成功跳转 | 填入“生成 AI 日报”，点启动 | 进入 RunLive |
| FE-02 | 新建任务失败提示 | 后端不可达时点启动 | NewRun 显示错误框 |
| FE-03 | RunLive 显示失败 | 后台返回 `graph.error` | 页面显示“生成任务失败” |
| FE-04 | RunLive 流式输出 | WriterAgent emit token | 文本区逐步增长 |
| FE-05 | 今日草稿箱 | 点 Dashboard “今日草稿” | 展开草稿箱 |
| FE-06 | 草稿进入编辑器 | 点草稿箱条目 | 打开 ArticleEditor 并显示草稿 |

### 端到端演示层

| ID | 用例 | 步骤 | 期望 |
|---|---|---|---|
| E2E-01 | mock 全链路 | 前端创建 mock run | 1 分钟内 done，有草稿和事件 |
| E2E-02 | 真实 MiMo 短任务 | 输入“生成 300 字 AI 日报” | Writer 有流式输出，最终 done |
| E2E-03 | 刷新回放 | run 完成后刷新页面 | 事件和草稿仍能回显 |
| E2E-04 | 中止任务 | 运行中点击中止 | 状态 aborted/failed，任务不再继续 |

## 4. 自动化建议

优先补 3 类测试：

1. `tests/api/test_runs_lifecycle.py`：覆盖 create → status → events → export。
2. `tests/api/test_run_failure_visibility.py`：覆盖图编译或 DB 失败时返回 `graph.error`。
3. `frontend` Playwright 测试：覆盖 NewRun 点击、RunLive 错误提示、今日草稿箱展开。

## 5. 每次提交前最小验证

```bash
cd /Users/gongbenxi/Documents/aistudy/code/Skills_Repo-main/ai-content-factory
.venv/bin/pytest -q
cd frontend
npm run build
```

人工验证：

1. 打开 `http://127.0.0.1:8000/`。
2. 新建生成任务：输入“生成一篇 AI 日报”。
3. 确认 RunLive 有事件、错误或正文，不能空白无反馈。
4. 回 Dashboard，点击“今日草稿”，确认草稿箱出现。

