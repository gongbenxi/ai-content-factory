"""预算熔断 — Token 模式 + 金额模式双熔断"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import yaml

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "models.yaml"


class BudgetExceeded(Exception):
    def __init__(self, message: str, run_id: str = "", tokens_used: int = 0):
        super().__init__(message)
        self.run_id = run_id
        self.tokens_used = tokens_used


def _load_budget_cfg() -> dict:
    with open(_CONFIG_PATH) as f:
        cfg = yaml.safe_load(f)
    return cfg.get("budget", {})


class BudgetGuard:
    def __init__(self, run_id: str, total_tokens_used: int = 0, warn_callback: Callable | None = None):
        self.run_id = run_id
        self.total_tokens_used = total_tokens_used
        self.warn_callback = warn_callback
        self._warned = False
        cfg = _load_budget_cfg()
        self.max_tokens = cfg.get("max_tokens_per_run", 200_000)
        self.warn_pct = cfg.get("warn_at_percent", 80)
        self.fallback_tier = cfg.get("fallback_tier", "fast")
        self.budget_limit_cents = cfg.get("budget_limit_cents", 300)

    def check_before_call(self, current_tier: str) -> tuple[str, bool]:
        """检查预算，返回 (effective_tier, should_warn)"""
        pct = (self.total_tokens_used / self.max_tokens * 100) if self.max_tokens else 0

        if pct >= 100:
            raise BudgetExceeded(
                f"Token 预算已用尽: {self.total_tokens_used}/{self.max_tokens}",
                run_id=self.run_id,
                tokens_used=self.total_tokens_used,
            )

        should_warn = pct >= self.warn_pct

        # 首次触发警告时 emit 事件
        if should_warn and not self._warned and self.warn_callback:
            self._warned = True
            self.warn_callback({
                "pct": round(pct, 1),
                "tokens_used": self.total_tokens_used,
                "max_tokens": self.max_tokens,
            })

        tier = self.fallback_tier if should_warn and current_tier != self.fallback_tier else current_tier
        return tier, should_warn

    def add_usage(self, usage: dict):
        self.total_tokens_used += usage.get("total_tokens", 0)

    def check_cost(self, total_cost_cents: int):
        if total_cost_cents >= self.budget_limit_cents:
            raise BudgetExceeded(
                f"金额预算已超限: {total_cost_cents}/{self.budget_limit_cents} cents",
                run_id=self.run_id,
            )
