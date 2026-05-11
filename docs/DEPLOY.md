# 部署指南

## 架构概览

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Frontend   │────▶│  FastAPI     │────▶│  PostgreSQL │
│  (Vite/React)│     │  (uvicorn)   │     │  (可选)     │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────┴───────┐
                    │  LangGraph   │
                    │  8-Agent     │
                    │  Pipeline    │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ LLM API  │ │ Tavily   │ │SiliconFlow│
        │ (MiMo/   │ │ Search   │ │ Image    │
        │ DeepSeek/│ │          │ │          │
        │ OpenAI)  │ │          │ │          │
        └──────────┘ └──────────┘ └──────────┘
```

## 环境要求

- Python 3.10+
- Node.js 18+（前端构建）
- PostgreSQL 15+（可选，无 PG 时自动降级到内存存储）

## 快速启动（开发模式）

### 1. 安装后端依赖

```bash
cd ai-content-factory
pip install -r requirements.txt
# 或手动安装核心依赖：
pip install fastapi uvicorn pydantic pyyaml httpx openai sse-starlette python-dotenv
pip install sqlalchemy psycopg[binary] alembic  # 可选：PostgreSQL 支持
pip install langgraph tavily-python pillow beautifulsoup4  # Agent + 工具
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 API Keys：
```

| 变量 | 说明 | 必填 |
|------|------|------|
| `MIMO_API_KEY` | 小米 MiMo API Key | 是（默认 provider） |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 否 |
| `OPENAI_API_KEY` | OpenAI API Key | 否 |
| `TAVILY_API_KEY` | Tavily 搜索 Key | 是（研究阶段） |
| `COZE_API_KEY` | Coze API（图像） | 否 |
| `SILICONFLOW_API_KEY` | 硅基流动（图像） | 否 |
| `DATABASE_URL` | PostgreSQL 连接串 | 否 |
| `LANGFUSE_SECRET_KEY` | Langfuse 追踪 | 否 |
| `LANGFUSE_PUBLIC_KEY` | Langfuse 追踪 | 否 |

### 3. 启动后端

```bash
python3 -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API 文档：http://localhost:8000/docs

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端：http://localhost:5173

## 生产部署

### PostgreSQL 配置

```bash
# 创建数据库
createdb ai_content_factory

# 设置连接串
export DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/ai_content_factory"

# 初始化表（首次）
python3 -c "
import asyncio
from app.db.session import init_db
asyncio.run(init_db())
"
```

### 前端构建

```bash
cd frontend
npm run build
# 构建产物在 frontend/dist/
# FastAPI 会自动挂载静态文件
```

### 使用 Gunicorn + Uvicorn

```bash
pip install gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Docker 部署

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 构建前端
RUN apt-get update && apt-get install -y nodejs npm && \
    cd frontend && npm install && npm run build && \
    apt-get clean

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # SSE 支持
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 900s;
    }

    location /data/images/ {
        alias /path/to/ai-content-factory/data/images/;
        expires 7d;
    }
}
```

## 监控与追踪

### Langfuse（可选）

设置环境变量后，每次 LLM 调用会自动记录 prompt、completion、cost、latency：

```bash
export LANGFUSE_SECRET_KEY="sk-lf-..."
export LANGFUSE_PUBLIC_KEY="pk-lf-..."
export LANGFUSE_HOST="https://cloud.langfuse.com"  # 或自建
```

### 健康检查

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

## 配置说明

模型和预算配置在 `config/models.yaml`：

```yaml
defaults:
  active_provider: xiaomi    # 默认 provider

providers:
  xiaomi:
    base_url: "https://token-plan-cn.xiaomimimo.com/v1"
    api_key_env: "MIMO_API_KEY"
    models:
      fast: "mimo-v2.5"
      balanced: "mimo-v2.5-pro"

# 每个 agent 可以独立选择 provider 和 tier
agents:
  topic:      { provider: xiaomi, tier: fast }
  writer:     { provider: xiaomi, tier: balanced }

# 预算控制
budget:
  max_tokens_per_run: 200000   # 单 run token 上限
  warn_at_percent: 80          # 降级阈值
  budget_limit_cents: 300      # 付费 provider 金额上限
```

通过 API 或前端 Settings 页面修改配置。

## 故障排查

| 现象 | 原因 | 解决 |
|------|------|------|
| 启动报 `ModuleNotFoundError` | 依赖未安装 | `pip install -r requirements.txt` |
| 图片显示为空 | `SILICONFLOW_API_KEY` 未设置 | 设置 key 或接受 placeholder 图片 |
| 数据不持久化 | PostgreSQL 未配置 | 配置 `DATABASE_URL` 或接受内存模式 |
| SSE 连接断开 | Nginx 代理超时 | 添加 `proxy_read_timeout 900s` |
| 任务超时 | 超过 15 分钟 | 检查 LLM API 响应速度，或增大 `_RUN_TIMEOUT_SECONDS` |
