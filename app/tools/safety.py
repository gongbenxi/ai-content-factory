"""内容安全工具 — 自建敏感词表"""

from __future__ import annotations

import re
from pathlib import Path

# 默认敏感词表
DEFAULT_KEYWORDS = [
    "赌博", "色情", "暴力", "恐怖", "毒品", "枪支", "假证",
    "代开发票", "套现", "传销", "诈骗", "高利贷",
]

_SENSITIVE_PATTERN = None


def _build_pattern() -> re.Pattern:
    global _SENSITIVE_PATTERN
    if _SENSITIVE_PATTERN is None:
        keywords = DEFAULT_KEYWORDS
        kw_file = Path(__file__).resolve().parent / "sensitive_words.txt"
        if kw_file.exists():
            keywords = [w.strip() for w in kw_file.read_text().splitlines() if w.strip()]
        escaped = [re.escape(kw) for kw in keywords]
        _SENSITIVE_PATTERN = re.compile("|".join(escaped))
    return _SENSITIVE_PATTERN


def content_safety_check(text: str) -> dict:
    """检查文本是否包含敏感词。

    Returns:
        {"safe": bool, "issues": [{"keyword": str, "position": int}]}
    """
    pattern = _build_pattern()
    issues = []
    for m in pattern.finditer(text):
        issues.append({
            "keyword": m.group(),
            "position": m.start(),
        })

    return {
        "safe": len(issues) == 0,
        "issues": issues,
        "total_hits": len(issues),
    }
