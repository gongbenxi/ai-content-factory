# AI Content Factory

多 Agent 化的中文图文生成流水线。8 个专业 Agent 协同工作，从选题到成稿一站式完成。

## 架构

```
TopicAgent → PlannerAgent → Researcher×N → EditorAgent
    → WriterAgent → IllustratorAgent → ReviewerAgent → ReviserAgent (最多 2 轮)
```

- **后端**: FastAPI + LangGraph 状态机
- **前端**: React + TypeScript + shadcn/ui + Tailwind
- **LLM**: 小米 MiMo / DeepSeek / OpenAI（可切换）
- **图像**: 硅基流动 AI 生图 + Pillow/Playwright/Pyecharts 混合方案
- **存储**: PostgreSQL（可选，无 PG 自动降级到内存）

## 快速开始

```bash
# 1. 配置环境变量
cp .env.example .env
# 填入 MIMO_API_KEY, TAVILY_API_KEY 等

# 2. 安装后端依赖
pip install fastapi uvicorn pydantic pyyaml httpx openai \
    sse-starlette python-dotenv langgraph tavily-python \
    pillow beautifulsoup4 sqlalchemy psycopg[binary]

# 3. 启动后端
python3 -m uvicorn app.main:app --reload --port 8000

# 4. 启动前端
cd frontend && npm install && npm run dev
```

前端：http://localhost:5173 | API 文档：http://localhost:8000/docs

## 功能

| 页面 | 功能 |
|------|------|
| **Dashboard** | KPI 统计、成本趋势、最近任务列表 |
| **New Run** | 选择风格/平台、配置并行度/预算、一键启动生成 |
| **Article Editor** | Markdown 编辑器、公众号预览、风格雷达图、配图管理、一键重新生成图片 |
| **Style Manager** | 从文章 URL 抽取风格指纹、高频词分布、句法特征分析 |
| **Settings** | Provider 切换、Per-Agent 模型分配、Token 预算、API Key 管理 |

## API 端点

```
POST   /api/runs                      # 创建生成任务
GET    /api/runs                      # 任务列表
GET    /api/runs/{id}                 # 任务详情
GET    /api/runs/{id}/stream          # SSE 实时事件流
POST   /api/runs/{id}/interrupt       # 人工介入
POST   /api/runs/{id}/resume          # 修改后继续
POST   /api/runs/{id}/abort           # 中止任务
PUT    /api/runs/{id}/article         # 编辑草稿
POST   /api/runs/{id}/complete        # 标记完成
POST   /api/runs/{id}/regenerate-image # 重新生成配图
GET    /api/runs/{id}/export          # 导出 Markdown

GET    /api/topics/candidates         # 候选选题
POST   /api/topics/refresh            # 刷新选题

GET    /api/styles                    # 风格列表
POST   /api/styles                    # 新增风格
POST   /api/styles/{id}/analyze       # 从 URL 抽取风格指纹

GET    /api/stats/dashboard           # Dashboard KPI
GET    /api/stats/cost                # 成本趋势

GET    /api/settings                  # 读取配置
PUT    /api/settings                  # 更新配置（带 schema 校验）
```

## 配置

模型和预算在 `config/models.yaml` 中管理（也可通过前端 Settings 页面修改）：

```yaml
defaults:
  active_provider: xiaomi

agents:
  topic:      { provider: xiaomi, tier: fast }
  writer:     { provider: xiaomi, tier: balanced }

budget:
  max_tokens_per_run: 200000
  warn_at_percent: 80
  budget_limit_cents: 300
```

## 部署

详见 [docs/DEPLOY.md](docs/DEPLOY.md)

## 文档

- [PRD](docs/PRD.md) — 产品需求文档
- [部署指南](docs/DEPLOY.md) — 生产环境部署
- [设计稿](docs/design-mockups.html) — 浏览器打开查看 UI 设计
