"""graph.py 测试 — 确认图构建成功"""

from app.agents.graph import build_graph, ContentState


def test_build_graph():
    g = build_graph()
    compiled = g.compile()
    assert compiled is not None


def test_content_state_fields():
    state: ContentState = {
        "run_id": "x",
        "user_request": "test",
        "user_preferences": {},
        "target_platform": "wechat",
        "style_id": None,
        "topic": None,
        "outline": None,
        "sub_queries": None,
        "snippets": [],
        "final_outline": None,
        "draft_md": None,
        "images": [],
        "review": None,
        "revise_count": 0,
        "cost_cents": 0,
        "usage_by_agent": {},
    }
    assert state["run_id"] == "x"
    assert state["revise_count"] == 0
