import re
import logging

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

FIRECRAWL_BASE = "https://api.firecrawl.dev/v1"


async def scrape_website(url: str) -> dict:
    if settings.dev_mode and not settings.firecrawl_api_key:
        from app.services.mock import mock_website
        return mock_website(url)

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{FIRECRAWL_BASE}/scrape",
                headers={"Authorization": f"Bearer {settings.firecrawl_api_key}"},
                json={"url": url, "formats": ["markdown", "rawHtml"]},
            )
        response.raise_for_status()
        data = response.json()
        page_data = data.get("data", {})
        metadata = page_data.get("metadata", {})

        markdown = page_data.get("markdown", "")
        raw_html = page_data.get("rawHtml", "")

        # --- Links: prefer Firecrawl's extracted links, fallback to parsing HTML ---
        links = page_data.get("links", [])
        if len(links) < 3 and raw_html:
            # Parse internal links from HTML
            domain = url.split("//")[1].split("/")[0] if "//" in url else ""
            html_hrefs = re.findall(r'href="([^"]*)"', raw_html)
            internal = set()
            for href in html_hrefs:
                if href.startswith("/") and not href.startswith("//"):
                    internal.add(href)
                elif domain and domain in href:
                    internal.add(href)
            links = list(internal)
            logger.info("Parsed %d internal links from HTML (Firecrawl returned %d)",
                         len(links), len(page_data.get("links", [])))

        # --- Schema: check HTML for ld+json (markdown strips <script> tags) ---
        has_schema = False
        schema_types = []
        if raw_html:
            schema_blocks = re.findall(
                r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>',
                raw_html, re.DOTALL
            )
            for block in schema_blocks:
                has_schema = True
                try:
                    import json
                    parsed = json.loads(block)
                    if isinstance(parsed, dict):
                        schema_types.append(parsed.get("@type", ""))
                    elif isinstance(parsed, list):
                        for item in parsed:
                            if isinstance(item, dict):
                                schema_types.append(item.get("@type", ""))
                except Exception:
                    pass

        # Also check markdown as fallback
        if not has_schema:
            has_schema = "schema.org" in markdown or "LocalBusiness" in markdown

        # --- Blog: check HTML for blog references ---
        has_blog = False
        if any("blog" in str(l).lower() for l in links):
            has_blog = True
        elif raw_html and re.search(r'href="[^"]*blog[^"]*"', raw_html, re.IGNORECASE):
            has_blog = True
        elif "blog" in markdown.lower():
            has_blog = True

        return {
            "content": markdown,
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "links": links,
            "has_schema": has_schema,
            "schema_types": schema_types,
            "has_blog": has_blog,
            "error": None,
        }
    except Exception as e:
        logger.error("Failed to scrape %s: %s", url, e)
        return {
            "content": "",
            "title": "",
            "description": "",
            "links": [],
            "has_schema": None,  # None = could not check (vs False = checked and missing)
            "schema_types": [],
            "has_blog": None,
            "error": str(e),
        }
