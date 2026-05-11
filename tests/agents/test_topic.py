"""topic agent 测试（mock 模式）"""

import pytest
from app.agents.topic import topic_agent


@pytest.mark.asyncio
async def test_topic_agent_mock():
    request = "外交部介绍特朗普访华安排和中方期待"
    state = {
        "run_id": "test-run",
        "user_request": request,
        "user_preferences": {},
        "target_platform": "wechat",
    }
    config = {"configurable": {"mock": True, "run_id": "test-run"}}

    result = await topic_agent(state, config)

    assert "topic" in result
    assert isinstance(result["topic"], dict)
    assert "title" in result["topic"]
    assert result["topic"]["title"] == request
    assert "target_platform" in result
