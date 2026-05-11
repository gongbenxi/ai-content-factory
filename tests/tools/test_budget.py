"""budget.py 单元测试"""

import pytest
from unittest.mock import patch
from app.llm.budget import BudgetGuard, BudgetExceeded


@pytest.fixture
def budget_cfg():
    return {
        "max_tokens_per_run": 10000,
        "warn_at_percent": 80,
        "fallback_tier": "fast",
        "budget_limit_cents": 100,
    }


@pytest.fixture
def guard(budget_cfg):
    with patch("app.llm.budget._load_budget_cfg", return_value=budget_cfg):
        return BudgetGuard("test-run-id")


def test_under_budget(guard):
    tier, warn = guard.check_before_call("balanced")
    assert tier == "balanced"
    assert warn is False


def test_warn_at_80pct(guard):
    guard.total_tokens_used = 8500
    tier, warn = guard.check_before_call("balanced")
    assert tier == "fast"
    assert warn is True


def test_budget_exceeded(guard):
    guard.total_tokens_used = 10000
    with pytest.raises(BudgetExceeded):
        guard.check_before_call("balanced")


def test_add_usage(guard):
    guard.add_usage({"total_tokens": 500})
    assert guard.total_tokens_used == 500
    guard.add_usage({"total_tokens": 300})
    assert guard.total_tokens_used == 800


def test_cost_check(guard):
    with pytest.raises(BudgetExceeded):
        guard.check_cost(200)


def test_cost_under_limit(guard):
    guard.check_cost(50)
