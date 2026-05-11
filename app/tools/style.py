"""风格指纹工具 — 从 skills/style_fingerprint 提取

分析中文文本的写作风格，输出指纹 JSON。
"""

from __future__ import annotations

import re
import json
from collections import Counter


def analyze_style(text: str) -> dict:
    """分析中文文本风格，返回风格指纹 JSON。

    输入至少 1KB 中文文本。
    """
    sentences = _split_sentences(text)
    words = _extract_words(text)

    return {
        "syntax_patterns": _analyze_syntax(sentences),
        "top_words": _top_words(words, n=30),
        "rhetorical_features": _analyze_rhetoric(text, sentences),
        "sentence_stats": {
            "avg_length": round(sum(len(s) for s in sentences) / max(len(sentences), 1)),
            "count": len(sentences),
        },
        "examples": sentences[:5],
    }


def _split_sentences(text: str) -> list[str]:
    """按中文标点分句"""
    parts = re.split(r'[。！？；\n]+', text)
    return [s.strip() for s in parts if len(s.strip()) > 5]


def _extract_words(text: str) -> list[str]:
    """简单的中文词提取（基于标点和空格分词）"""
    # 去除标点
    clean = re.sub(r'[^一-鿿\w\s]', ' ', text)
    # 简单按空格和常见分隔符分词
    raw = re.split(r'\s+', clean)
    return [w for w in raw if len(w) >= 2]


def _top_words(words: list[str], n: int = 30) -> list[dict]:
    """高频词统计"""
    counter = Counter(words)
    return [{"word": w, "count": c} for w, c in counter.most_common(n)]


def _analyze_syntax(sentences: list[str]) -> dict:
    """句法特征分析"""
    if not sentences:
        return {"short_sentence_ratio": 0, "question_ratio": 0, "exclamation_ratio": 0}

    short = sum(1 for s in sentences if len(s) < 20)
    questions = sum(1 for s in sentences if s.endswith("？") or s.endswith("?"))
    exclamations = sum(1 for s in sentences if s.endswith("！") or s.endswith("!"))

    total = len(sentences)
    return {
        "short_sentence_ratio": round(short / total, 2),
        "question_ratio": round(questions / total, 2),
        "exclamation_ratio": round(exclamations / total, 2),
    }


def _analyze_rhetoric(text: str, sentences: list[str]) -> dict:
    """修辞偏好分析"""
    quotes = len(re.findall(r'[""“”]', text))
    lists = len(re.findall(r'^\s*[\d一二三四五六七八九十]+[.、]', text, re.MULTILINE))
    metaphors = len(re.findall(r'(?:像|如同|仿佛|犹如|好似)', text))

    return {
        "uses_quotes": quotes > 2,
        "quote_count": quotes,
        "uses_lists": lists > 0,
        "list_count": lists,
        "metaphor_count": metaphors,
    }
