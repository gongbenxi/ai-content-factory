"""Shared API error helpers."""

from __future__ import annotations

from fastapi import HTTPException
from openai import APIStatusError
from tenacity import RetryError


def raise_llm_http_error(exc: Exception, *, action: str = "LLM 调用失败") -> None:
    """Convert provider/client exceptions into stable HTTP error payloads."""
    detail = format_llm_error(exc, action=action)
    status_code = detail.pop("status_code")
    raise HTTPException(status_code=status_code, detail=detail)


def format_llm_error(exc: Exception, *, action: str = "LLM 调用失败") -> dict:
    """Return a stable provider error payload suitable for APIs and run events."""
    root = _unwrap_retry_error(exc)
    status_code = 502
    code = "LLM_PROVIDER_ERROR"
    message = str(root)
    provider_status = getattr(root, "status_code", None)
    provider_body = getattr(root, "body", None)

    if isinstance(root, KeyError):
        status_code = 424
        code = "LLM_API_KEY_MISSING"
        message = f"缺少模型服务环境变量：{root}"
    elif isinstance(root, APIStatusError):
        status_code = 424 if root.status_code in {402, 403} else 502
        message = _provider_message(root) or message
        if _is_insufficient_balance(root):
            code = "LLM_INSUFFICIENT_BALANCE"
        elif _is_model_disabled(root):
            code = "LLM_MODEL_DISABLED"
        else:
            code = f"LLM_HTTP_{root.status_code}"

    return {
        "status_code": status_code,
        "code": code,
        "message": message,
        "action": action,
        "provider_status": provider_status,
        "provider_body": provider_body if isinstance(provider_body, dict) else None,
    }


def _unwrap_retry_error(exc: Exception) -> Exception:
    if isinstance(exc, RetryError):
        try:
            return exc.last_attempt.exception() or exc
        except Exception:
            return exc
    return exc


def _provider_message(exc: APIStatusError) -> str | None:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        message = body.get("message")
        if isinstance(message, str):
            return message
        error = body.get("error")
        if isinstance(error, dict) and isinstance(error.get("message"), str):
            return error["message"]
    return None


def _is_model_disabled(exc: APIStatusError) -> bool:
    body = getattr(exc, "body", None)
    if isinstance(body, dict) and body.get("code") == 30003:
        return True
    return "Model disabled" in str(exc)


def _is_insufficient_balance(exc: APIStatusError) -> bool:
    text = str(getattr(exc, "body", None) or exc)
    return exc.status_code == 402 or "Insufficient Balance" in text or "余额" in text
