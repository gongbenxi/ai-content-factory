"""模型定价表 — 每 1M token 价格（单位：cent）"""

from __future__ import annotations


# {provider: {tier: {input_cents_per_1m, output_cents_per_1m}}}
MODEL_PRICING: dict[str, dict[str, dict[str, int]]] = {
    "xiaomi": {
        "fast":    {"input_cents_per_1m": 0,   "output_cents_per_1m": 0},
        "balanced": {"input_cents_per_1m": 0,  "output_cents_per_1m": 0},
    },
    "deepseek": {
        "fast":    {"input_cents_per_1m": 14,  "output_cents_per_1m": 28},
        "balanced": {"input_cents_per_1m": 14, "output_cents_per_1m": 28},
    },
    "openai": {
        "fast":    {"input_cents_per_1m": 15,  "output_cents_per_1m": 60},
        "balanced": {"input_cents_per_1m": 250, "output_cents_per_1m": 1000},
    },
}


def calc_cost(provider: str, tier: str, input_tokens: int, output_tokens: int) -> int:
    """计算 token 使用成本，返回 cent 整数"""
    pricing = MODEL_PRICING.get(provider, {}).get(tier, {})
    input_rate = pricing.get("input_cents_per_1m", 0)
    output_rate = pricing.get("output_cents_per_1m", 0)
    cost = (input_tokens * input_rate + output_tokens * output_rate) / 1_000_000
    return round(cost)
