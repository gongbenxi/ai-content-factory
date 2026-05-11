"""image.py 单元测试"""

import pytest
from app.tools.image import parse_placeholders, render_with_images, _ratio_to_size


def test_parse_placeholders_basic():
    md = "开头\n\n[IMG: 测试图 | 16:9 | chart]\n\n结尾"
    result = parse_placeholders(md)
    assert len(result) == 1
    assert result[0]["description"] == "测试图"
    assert result[0]["ratio"] == "16:9"
    assert result[0]["type"] == "chart"


def test_parse_placeholders_multiple():
    md = "[IMG: 图1 | 16:9 | cover]\n正文\n[IMG: 图2 | 1:1 | card]\n结尾\n[IMG: 图3 | 3:4 | illustration]"
    result = parse_placeholders(md)
    assert len(result) == 3
    assert result[0]["type"] == "cover"
    assert result[1]["type"] == "card"
    assert result[2]["type"] == "illustration"


def test_parse_placeholders_empty():
    assert parse_placeholders("无占位符的文章") == []


def test_render_with_images():
    md = "前文\n[IMG: 描述 | 16:9 | chart]\n后文"
    phs = parse_placeholders(md)
    imgs = [{"url": "https://example.com/img.png"}]
    result = render_with_images(md, phs, imgs)
    assert "![描述](https://example.com/img.png)" in result
    assert "[IMG:" not in result


def test_ratio_to_size():
    assert _ratio_to_size("16:9") == "1024x576"
    assert _ratio_to_size("1:1") == "1024x1024"
    assert _ratio_to_size("unknown") == "1024x576"
