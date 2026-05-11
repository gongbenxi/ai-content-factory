"""Settings API — 模型/预算配置"""

from __future__ import annotations

import yaml
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "models.yaml"

_VALID_PROVIDERS = {"xiaomi", "deepseek", "openai"}
_VALID_TIERS = {"fast", "balanced"}
_VALID_AGENTS = {"topic", "researcher", "planner", "editor", "writer", "illustrator", "reviewer", "reviser"}


class AgentConfig(BaseModel):
    provider: str
    tier: str

    def model_post_init(self, __context):
        if self.provider not in _VALID_PROVIDERS:
            raise ValueError(f"Invalid provider: {self.provider}. Must be one of {_VALID_PROVIDERS}")
        if self.tier not in _VALID_TIERS:
            raise ValueError(f"Invalid tier: {self.tier}. Must be one of {_VALID_TIERS}")


class BudgetConfig(BaseModel):
    max_tokens_per_run: int = Field(ge=10_000, le=1_000_000, default=200_000)
    warn_at_percent: int = Field(ge=10, le=100, default=80)
    fallback_tier: str = "fast"
    budget_limit_cents: int = Field(ge=0, default=300)


class DefaultsConfig(BaseModel):
    active_provider: str = "xiaomi"

    def model_post_init(self, __context):
        if self.active_provider not in _VALID_PROVIDERS:
            raise ValueError(f"Invalid provider: {self.active_provider}")


class SettingsUpdate(BaseModel):
    defaults: DefaultsConfig = DefaultsConfig()
    providers: dict = {}
    agents: dict[str, AgentConfig] = {}
    budget: BudgetConfig = BudgetConfig()

    def model_post_init(self, __context):
        for key in self.agents:
            if key not in _VALID_AGENTS:
                raise ValueError(f"Unknown agent: {key}. Must be one of {_VALID_AGENTS}")


@router.get("")
async def get_settings():
    """读取配置"""
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


@router.put("")
async def update_settings(body: SettingsUpdate):
    """更新配置（带 schema 校验）"""
    data = body.model_dump()
    with open(_CONFIG_PATH, "w") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
    return {"updated": True}
