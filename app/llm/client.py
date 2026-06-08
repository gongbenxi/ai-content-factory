"""LLM 抽象层 — 多 Provider 路由 + mock 模式 + token 计量 + 预算熔断 + Langfuse"""

import os
import json
import time
from pathlib import Path
from typing import Any, AsyncIterator

import yaml
from openai import APIStatusError, AsyncOpenAI
from dotenv import load_dotenv
from tenacity import RetryError, retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.llm._mock import MOCK_RESPONSES, build_mock_response, mock_usage
from app.llm.budget import BudgetGuard, BudgetExceeded
from app.llm.pricing import calc_cost
from app.db.session import get_session
from app.db.models import TokenUsage
from app.observability.langfuse import get_langfuse, _langfuse_enabled

_CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "models.yaml"
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"

load_dotenv(_ENV_PATH)


def _load_config() -> dict:
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _get_client_for_provider(provider_cfg: dict) -> AsyncOpenAI:
    api_key = os.environ[provider_cfg["api_key_env"]]
    return AsyncOpenAI(api_key=api_key, base_url=provider_cfg["base_url"])


def resolve_model(agent: str, config: dict | None = None, tier_override: str | None = None) -> tuple[str, AsyncOpenAI, str, str]:
    """返回 (model_name, client, provider_name, tier)"""
    cfg = config or _load_config()
    agent_cfg = cfg["agents"].get(agent, cfg["agents"]["topic"])
    provider_name = agent_cfg["provider"]
    tier = tier_override or agent_cfg["tier"]
    provider_cfg = cfg["providers"][provider_name]
    model = provider_cfg["models"][tier]
    client = _get_client_for_provider(provider_cfg)
    return model, client, provider_name, tier


def _is_model_disabled_error(exc: Exception) -> bool:
    exc = _unwrap_retry_error(exc)
    if isinstance(exc, APIStatusError) and exc.status_code == 403:
        body = getattr(exc, "body", None)
        if isinstance(body, dict) and body.get("code") == 30003:
            return True
    return "Model disabled" in str(exc)


def _unwrap_retry_error(exc: Exception) -> Exception:
    if isinstance(exc, RetryError):
        try:
            return exc.last_attempt.exception() or exc
        except Exception:
            return exc
    return exc


def _should_retry_llm_error(exc: Exception) -> bool:
    root = _unwrap_retry_error(exc)
    if isinstance(root, APIStatusError) and root.status_code in {400, 401, 402, 403, 404}:
        return False
    return True


def _with_provider_defaults(provider: str, model: str, kw: dict) -> dict:
    """Provider-specific request defaults.

    DeepSeek V4 defaults to thinking mode, which can stream reasoning_content
    before final content. Writer/editor UI only renders content, so disable
    thinking unless the caller explicitly opts in.
    """
    if provider != "deepseek" or not model.startswith("deepseek-v4"):
        return kw
    next_kw = dict(kw)
    extra_body = dict(next_kw.get("extra_body") or {})
    extra_body.setdefault("thinking", {"type": "disabled"})
    next_kw["extra_body"] = extra_body
    return next_kw


async def _write_token_usage(run_id: str, agent: str, usage: dict):
    """写入 token_usage 表"""
    try:
        async with get_session() as session:
            row = TokenUsage(
                run_id=run_id,
                agent=agent,
                provider=usage.get("provider", ""),
                model=usage.get("model", ""),
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                cache_read_tokens=usage.get("cache_read_tokens", 0),
                cost_cents=usage.get("cost_cents", 0),
                latency_ms=usage.get("latency_ms"),
            )
            session.add(row)
            await session.commit()
    except Exception:
        pass


def _trace_to_langfuse(agent: str, messages: list[dict], content: str, usage: dict, latency_ms: int):
    """上报到 Langfuse（fire-and-forget）"""
    if not _langfuse_enabled:
        return
    try:
        lf = get_langfuse()
        trace = lf.trace(name=f"llm:{agent}", metadata={"agent": agent})
        trace.span(
            name="llm_call",
            input=messages,
            output=content,
            usage=usage,
            metadata={"latency_ms": latency_ms, **usage},
        )
        lf.flush()
    except Exception:
        pass


class LLMClient:
    def __init__(self, run_id: str | None = None, budget: BudgetGuard | None = None):
        self.run_id = run_id
        self.budget = budget

    async def chat(self, agent: str, messages: list[dict], *, mock: bool = False, **kw) -> tuple[str, dict]:
        """返回 (content, usage_dict)"""
        if mock:
            resp_text = build_mock_response(agent, messages)
            return resp_text, mock_usage(resp_text)

        cfg = _load_config()
        agent_cfg = cfg["agents"].get(agent, cfg["agents"]["topic"])
        original_tier = agent_cfg["tier"]

        tier_override = None
        if self.budget:
            effective_tier, _warned = self.budget.check_before_call(original_tier)
            if effective_tier != original_tier:
                tier_override = effective_tier

        model, client, provider, tier = resolve_model(agent, cfg, tier_override)
        kw = _with_provider_defaults(provider, model, kw)

        start = time.monotonic()
        try:
            resp = await _call_with_retry(client, model, messages, **kw)
        except Exception as exc:
            fallback_tier = cfg.get("budget", {}).get("fallback_tier", "fast")
            if _is_model_disabled_error(exc) and tier != fallback_tier:
                model, client, provider, tier = resolve_model(agent, cfg, fallback_tier)
                resp = await _call_with_retry(client, model, messages, **kw)
            else:
                raise
        latency_ms = int((time.monotonic() - start) * 1000)

        usage = {
            "input_tokens": resp.usage.prompt_tokens,
            "output_tokens": resp.usage.completion_tokens,
            "cache_read_tokens": getattr(resp.usage, "prompt_tokens_details", None) and getattr(resp.usage.prompt_tokens_details, "cached_tokens", 0) or 0,
            "total_tokens": resp.usage.total_tokens,
            "latency_ms": latency_ms,
            "provider": provider,
            "model": model,
            "tier": tier,
            "cost_cents": calc_cost(provider, tier, resp.usage.prompt_tokens, resp.usage.completion_tokens),
        }

        if self.budget:
            self.budget.add_usage(usage)

        if self.run_id:
            await _write_token_usage(self.run_id, agent, usage)

        content = resp.choices[0].message.content
        _trace_to_langfuse(agent, messages, content, usage, latency_ms)

        return content, usage

    async def chat_json(self, agent: str, messages: list[dict], *, mock: bool = False, **kw) -> tuple[dict, dict]:
        """返回 (parsed_json, usage_dict)"""
        content, usage = await self.chat(agent, messages, mock=mock, **kw)
        try:
            return _parse_json_content(content), usage
        except Exception as exc:
            fallback = MOCK_RESPONSES.get(agent)
            if fallback:
                usage["json_parse_error"] = str(exc)
                return _parse_json_content(fallback), usage
            raise ValueError(f"{agent} returned invalid JSON: {(content or '')[:300]}") from exc

    async def stream(self, agent: str, messages: list[dict], *, mock: bool = False, **kw) -> AsyncIterator[str]:
        if mock:
            yield build_mock_response(agent, messages)
            return

        cfg = _load_config()
        agent_cfg = cfg["agents"].get(agent, cfg["agents"]["topic"])
        original_tier = agent_cfg["tier"]

        tier_override = None
        if self.budget:
            effective_tier, _warned = self.budget.check_before_call(original_tier)
            if effective_tier != original_tier:
                tier_override = effective_tier

        model, client, provider, tier = resolve_model(agent, cfg, tier_override)
        kw = _with_provider_defaults(provider, model, kw)

        try:
            stream = await client.chat.completions.create(
                model=model, messages=messages, stream=True, **kw
            )
        except Exception as exc:
            fallback_tier = cfg.get("budget", {}).get("fallback_tier", "fast")
            if _is_model_disabled_error(exc) and tier != fallback_tier:
                model, client, provider, tier = resolve_model(agent, cfg, fallback_tier)
                stream = await client.chat.completions.create(
                    model=model, messages=messages, stream=True, **kw
                )
            else:
                raise
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


@retry(
    retry=retry_if_exception(_should_retry_llm_error),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=30),
)
async def _call_with_retry(client: AsyncOpenAI, model: str, messages: list[dict], **kw) -> Any:
    max_tokens = kw.pop("max_tokens", 4096)
    return await client.chat.completions.create(
        model=model, messages=messages, max_tokens=max_tokens, **kw
    )


def _parse_json_content(content: str | None) -> Any:
    """Parse JSON from raw model content, including fenced or explanatory output."""
    text = (content or "").strip()
    if not text:
        raise ValueError("empty content")

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    candidates = []
    for opener, closer in [("{", "}"), ("[", "]")]:
        start = text.find(opener)
        end = text.rfind(closer)
        if start >= 0 and end > start:
            candidates.append(text[start:end + 1])

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except json.JSONDecodeError as exc:
            last_error = exc

    raise last_error or ValueError("no JSON object or array found")
