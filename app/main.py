"""FastAPI 入口 — 挂载 router + 静态文件 + CORS"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import runs, topics, styles, stats, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="AI Content Factory",
    description="多 Agent 化的中文图文生成流水线",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


# API routes
app.include_router(runs.router, prefix="/api/runs", tags=["runs"])
app.include_router(topics.router, prefix="/api/topics", tags=["topics"])
app.include_router(styles.router, prefix="/api/styles", tags=["styles"])
app.include_router(stats.router, prefix="/api/stats", tags=["stats"])
app.include_router(settings.router, prefix="/api/settings", tags=["settings"])

# 生成图片静态服务
data_images = Path("data/images")
data_images.mkdir(parents=True, exist_ok=True)
app.mount("/data/images", StaticFiles(directory=str(data_images)), name="data_images")

# 静态文件挂载（Vite 构建产物）— 必须在所有 API 路由之后
frontend_dist = Path(__file__).resolve().parents[1] / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
