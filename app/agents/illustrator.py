"""IllustratorAgent — 配图：基于段落生成 N 张图"""

from __future__ import annotations

from app.tools.image import parse_placeholders, enhance_prompt, generate_image, render_with_images
from app.workers.runner import emit_event


async def illustrator_agent(state: dict, config=None) -> dict:
    """LangGraph node: IllustratorAgent"""
    configurable = config.get("configurable", {}) if config else {}
    mock = configurable.get("mock", False)
    run_id = configurable.get("run_id") or state.get("run_id", "")

    await emit_event(run_id, "agent.start", {"agent": "illustrator"})

    draft_md = state.get("draft_md", "")

    if not draft_md:
        await emit_event(run_id, "agent.done", {"agent": "illustrator", "images": 0})
        return {"images": []}

    placeholders = parse_placeholders(draft_md)
    if not placeholders:
        await emit_event(run_id, "agent.done", {"agent": "illustrator", "images": 0})
        return {"images": []}

    style_id = state.get("style_id", "default")
    images = []

    for ph in placeholders:
        if mock:
            img = {
                "para_id": ph["para_id"],
                "type": ph["type"],
                "description": ph["description"],
                "url": f"/data/images/mock_{ph['para_id']}.png",
                "ratio": ph["ratio"],
                "model": "mock",
                "context_excerpt": ph["context_before"][-150:] if ph["context_before"] else "",
            }
        else:
            enhanced = await enhance_prompt(ph, style_id, mock=mock)
            result = await generate_image(enhanced, ph["type"], ph["ratio"])
            img = {
                "para_id": ph["para_id"],
                "type": ph["type"],
                "description": ph["description"],
                "enhanced_prompt": enhanced,
                "url": result.get("url", ""),
                "alt_urls": result.get("alt_urls", []),
                "ratio": ph["ratio"],
                "model": result.get("model", ""),
                "context_excerpt": ph["context_before"][-150:] if ph["context_before"] else "",
                "regenerate_count": 0,
            }

        images.append(img)
        await emit_event(run_id, "image.generated", {
            "para_id": ph["para_id"],
            "url": img.get("url", ""),
            "type": ph["type"],
        })

    updated_md = render_with_images(draft_md, placeholders, images) if not mock else draft_md

    await emit_event(run_id, "agent.done", {"agent": "illustrator", "images": len(images)})

    return {"images": images, "draft_md": updated_md}
