"""
路由 — /api/topics/*（对应 PRD §6b / §4.1）
================================================================
"""

from __future__ import annotations

from fastapi import APIRouter

from app.models import TopicListResponse, TopicCandidate

router = APIRouter(prefix="/api/topics", tags=["topics"])


@router.get("/candidates", response_model=TopicListResponse)
async def api_topic_candidates():
    """今日候选选题（对应 PRD M1 / §4.1 TopicAgent 输出）。

    Phase 1 实现：调用 graph 中的 topic_agent 逻辑，
    后续可独立为定时任务。
    """
    # TODO: 接入真实的 fetch_hotnews_unified + topic_agent
    # 当前返回 mock 数据，与 graph.py 中 _MOCK["topic"] 对齐
    return TopicListResponse(
        candidates=[
            TopicCandidate(
                title="DeepSeek-V3 发布带来的国产大模型竞争格局变化",
                angle="技术拐点 + 商业影响双线",
                target_platform="wechat",
                hook="六百万美元，把硅谷震了",
                estimated_quality=0.85,
            ),
            TopicCandidate(
                title="小红书种草笔记的 AI 写作工业化",
                angle="工具革命 + 平台治理冲突",
                target_platform="xhs",
                hook="一个人撑起一个 MCN 的时代来了",
                estimated_quality=0.78,
            ),
            TopicCandidate(
                title="A 股 AI 概念股泡沫预警",
                angle="数据驱动 + 历史对比",
                target_platform="wechat",
                hook="上次这么疯还是元宇宙",
                estimated_quality=0.72,
            ),
        ]
    )


@router.post("/refresh")
async def api_refresh_topics():
    """强制刷新选题。"""
    # TODO: 触发 topic_agent 重新运行
    return {"status": "refreshing", "message": "选题刷新已触发"}
