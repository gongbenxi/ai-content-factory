"""Langfuse 集成 — @trace_llm 装饰器"""

import os
import time
from functools import wraps

_langfuse_enabled = False
_langfuse = None


def _init_langfuse():
    global _langfuse, _langfuse_enabled
    try:
        from langfuse import Langfuse
        _langfuse = Langfuse(
            secret_key=os.getenv("LANGFUSE_SECRET_KEY", ""),
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
            host=os.getenv("LANGFUSE_HOST", "http://localhost:3000"),
        )
        _langfuse_enabled = bool(os.getenv("LANGFUSE_SECRET_KEY"))
    except ImportError:
        _langfuse_enabled = False


def get_langfuse():
    if _langfuse is None:
        _init_langfuse()
    return _langfuse


def trace_llm(agent: str):
    """装饰器：自动上报 prompt/completion/usage/latency 到 Langfuse"""

    def decorator(fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            if not _langfuse_enabled:
                return await fn(*args, **kwargs)

            lf = get_langfuse()
            start = time.monotonic()
            trace = lf.trace(name=f"llm:{agent}", metadata={"agent": agent})

            try:
                result = await fn(*args, **kwargs)
                latency_ms = int((time.monotonic() - start) * 1000)

                if isinstance(result, tuple) and len(result) == 2:
                    content, usage = result
                    trace.span(
                        name="llm_call",
                        input=kwargs.get("messages", args[1] if len(args) > 1 else []),
                        output=content,
                        usage=usage,
                        metadata={"latency_ms": latency_ms, **usage},
                    )
                lf.flush()
                return result
            except Exception as e:
                trace.update(metadata={"error": str(e)})
                lf.flush()
                raise

        return wrapper

    return decorator
