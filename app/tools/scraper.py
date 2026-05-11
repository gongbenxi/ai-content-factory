"""网页抓取工具 — Crawl4AI 封装"""

from __future__ import annotations


async def scrape_url(url: str) -> dict:
    """抓取网页内容，返回 {url, title, markdown, success}"""
    if not url:
        return {"url": url, "title": "", "markdown": "", "success": False}

    try:
        from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

        browser_cfg = BrowserConfig(headless=True)
        run_cfg = CrawlerRunConfig()

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)

        if result and result.markdown:
            md = result.markdown.raw_markdown if hasattr(result.markdown, "raw_markdown") else str(result.markdown)
            return {
                "url": url,
                "title": result.metadata.get("title", "") if result.metadata else "",
                "markdown": md[:5000],  # 截断避免 token 浪费
                "success": True,
            }
        return {"url": url, "title": "", "markdown": "", "success": False}
    except Exception as e:
        print(f"[scraper] 抓取失败 {url}: {e}")
        return {"url": url, "title": "", "markdown": "", "success": False, "error": str(e)}
