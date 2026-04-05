#!/usr/bin/env python3
"""
Test script to audit any business and validate our checks against reality.

Usage:
    python scripts/audit_test.py "Baran Bistro" "Berlin" "https://baranbistro.com"
    python scripts/audit_test.py "IKEA" "Berlin" "https://www.ikea.com/de/de/"
    python scripts/audit_test.py "McFit" "Berlin" "https://www.mcfit.com"

This script runs each check independently and shows EXACTLY what data we get,
so we can see where our checks are wrong.
"""

import asyncio
import json
import sys
import httpx

# ─── Config ──────────────────────────────────────────────────────────────────

SERPAPI_KEY = ""  # Set via env or hardcode for testing
FIRECRAWL_KEY = ""
YOUTUBE_KEY = ""

# Try to load from backend .env
try:
    with open("backend/.env") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k == "SERPAPI_KEY":
                SERPAPI_KEY = v
            elif k == "FIRECRAWL_API_KEY":
                FIRECRAWL_KEY = v
            elif k == "YOUTUBE_API_KEY":
                YOUTUBE_KEY = v
except FileNotFoundError:
    pass


client = httpx.AsyncClient(timeout=30.0)


def header(text: str):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")


def ok(text: str):
    print(f"  ✅ {text}")


def warn(text: str):
    print(f"  ⚠️  {text}")


def fail(text: str):
    print(f"  ❌ {text}")


def info(text: str):
    print(f"     {text}")


# ─── Google Maps Check ───────────────────────────────────────────────────────

async def check_google_maps(name: str, city: str):
    header("GOOGLE MAPS")

    if not SERPAPI_KEY:
        fail("No SERPAPI_KEY set")
        return

    # Search with name + city
    resp = await client.get("https://serpapi.com/search", params={
        "engine": "google_maps", "q": f"{name} {city}", "api_key": SERPAPI_KEY,
    })
    data = resp.json()

    # Check place_results (direct match)
    pr = data.get("place_results")
    if pr:
        ok(f"Direct match found: {pr.get('title')}")
        info(f"Rating: {pr.get('rating')} ({pr.get('reviews')} reviews)")
        info(f"Address: {pr.get('address')}")
        info(f"Place ID: {pr.get('place_id')}")
        info(f"Type: {pr.get('type')}")
        return pr

    # Check local_results
    results = data.get("local_results", [])
    if results:
        found = None
        for r in results:
            if name.lower() in r.get("title", "").lower():
                found = r
                break
        if found:
            ok(f"Found in local results: {found.get('title')} (position #{found.get('position')})")
            info(f"Rating: {found.get('rating')} ({found.get('reviews')} reviews)")
            return found
        else:
            warn(f"Got {len(results)} results but none match '{name}'")
            for r in results[:3]:
                info(f"  - {r.get('title')}")
    else:
        fail(f"No results for '{name} {city}'")

    return None


# ─── Website Check ───────────────────────────────────────────────────────────

async def check_website(url: str):
    header("WEBSITE & SEO")

    if not url:
        fail("No website URL provided")
        return

    if not FIRECRAWL_KEY:
        fail("No FIRECRAWL_API_KEY set")
        return

    # Scrape with BOTH markdown and HTML
    resp = await client.post("https://api.firecrawl.dev/v1/scrape", headers={
        "Authorization": f"Bearer {FIRECRAWL_KEY}",
    }, json={
        "url": url,
        "formats": ["markdown", "rawHtml"],
    })
    data = resp.json()

    if not data.get("success"):
        fail(f"Firecrawl failed: {data.get('error', 'unknown')}")
        return

    page = data.get("data", {})
    md = page.get("markdown", "")
    html = page.get("rawHtml", "")
    meta = page.get("metadata", {})
    links = page.get("links", [])

    print(f"\n  --- Raw Data ---")
    info(f"Title: {meta.get('title', 'MISSING')}")
    info(f"Description: {(meta.get('description', 'MISSING'))[:100]}")
    info(f"Markdown length: {len(md)} chars")
    info(f"HTML length: {len(html)} chars")
    info(f"Links from Firecrawl: {len(links)}")

    print(f"\n  --- Our Current Checks ---")

    # Check 1: Content length (markdown)
    if len(md) > 500:
        ok(f"Content length {len(md)} chars (500+ ✓)")
    else:
        fail(f"Content length {len(md)} chars (need 500+)")

    # Check 2: Meta description
    if meta.get("description"):
        ok(f"Meta description: {meta['description'][:80]}...")
    else:
        fail("No meta description")

    # Check 3: Links
    if len(links) >= 3:
        ok(f"{len(links)} links found (3+ ✓)")
    else:
        # Firecrawl often returns 0 links for JS-heavy sites
        # Let's count links in HTML as fallback
        import re
        html_links = re.findall(r'href="([^"]*)"', html) if html else []
        internal_links = [l for l in html_links if l.startswith("/") or url.split("//")[1].split("/")[0] in l]
        if len(internal_links) >= 3:
            warn(f"Firecrawl returned {len(links)} links, but HTML has {len(internal_links)} internal links")
            info("⚡ Our check is WRONG — should parse HTML links as fallback")
        else:
            fail(f"{len(links)} links found (need 3+)")

    # Check 4: Schema markup
    # Current: search markdown for "schema.org" or "LocalBusiness"
    schema_in_md = "schema.org" in md or "LocalBusiness" in md
    schema_in_html = 'application/ld+json' in html if html else False

    if schema_in_md:
        ok("Schema markup found in markdown")
    elif schema_in_html:
        warn("Schema markup found in HTML but NOT in markdown")
        info("⚡ Our check is WRONG — we only check markdown, missing <script> tags")
        # Extract and show the schema
        import re
        schemas = re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', html, re.DOTALL)
        for s in schemas[:2]:
            try:
                parsed = json.loads(s)
                schema_type = parsed.get("@type", "unknown")
                info(f"  Found: @type={schema_type}")
            except json.JSONDecodeError:
                info(f"  Found ld+json block ({len(s)} chars)")
    else:
        fail("No Schema markup found in markdown or HTML")

    # Check 5: Page title
    if meta.get("title"):
        ok(f"Page title: {meta['title']}")
    else:
        fail("No page title")

    # Check 6: Blog
    all_links_text = " ".join(links) + " " + md
    if "blog" in all_links_text.lower():
        ok("Blog link found")
    elif html and "blog" in html.lower():
        warn("Blog reference found in HTML but not in markdown/links")
        info("⚡ Our check might miss this")
    else:
        fail("No blog link found")

    return {"md": md, "html": html, "meta": meta, "links": links}


# ─── Local Authority Check ───────────────────────────────────────────────────

async def check_local_authority(name: str, city: str):
    header("LOCAL AUTHORITY")

    if not SERPAPI_KEY:
        fail("No SERPAPI_KEY set")
        return

    total_sources = []
    on_best_of = False

    for query in [f"{name} {city} best", f"{name} review blog"]:
        resp = await client.get("https://serpapi.com/search", params={
            "engine": "google", "q": query, "api_key": SERPAPI_KEY, "num": 10,
        })
        data = resp.json()

        organic = data.get("organic_results", [])
        info(f"Query: '{query}' → {len(organic)} results")

        for r in organic:
            title = r.get("title", "")
            snippet = r.get("snippet", "")
            url = r.get("link", "")
            if name.lower() in (title + snippet).lower():
                total_sources.append({"title": title, "url": url})
                if any(kw in title.lower() for kw in ["best", "top ", "ranked"]):
                    on_best_of = True

    unique = {s["url"]: s for s in total_sources}
    print(f"\n  --- Results ---")
    if unique:
        ok(f"{len(unique)} mentions found")
        for s in list(unique.values())[:5]:
            info(f"  → {s['title'][:70]}")
            info(f"    {s['url'][:80]}")
    else:
        fail("No mentions found")

    if on_best_of:
        ok("Featured on a 'best of' list")
    else:
        warn("Not found on any 'best of' list")


# ─── YouTube Check ───────────────────────────────────────────────────────────

async def check_youtube(name: str, city: str):
    header("YOUTUBE")

    if not YOUTUBE_KEY:
        fail("No YOUTUBE_API_KEY set")
        return

    # Video search
    resp = await client.get("https://www.googleapis.com/youtube/v3/search", params={
        "part": "snippet", "q": f"{name} {city}", "type": "video",
        "maxResults": 10, "key": YOUTUBE_KEY,
    })
    data = resp.json()
    items = data.get("items", [])

    name_lower = name.lower()
    confirmed = []
    possible = []

    for item in items:
        snippet = item.get("snippet", {})
        title = snippet.get("title", "")
        desc = snippet.get("description", "")[:200]
        vid = {
            "title": title,
            "channel": snippet.get("channelTitle"),
            "video_id": item.get("id", {}).get("videoId"),
        }
        if name_lower in title.lower() or name_lower in desc.lower():
            confirmed.append(vid)
        else:
            possible.append(vid)

    print(f"\n  --- Results ---")
    if confirmed:
        ok(f"{len(confirmed)} videos directly mention '{name}'")
        for v in confirmed[:3]:
            info(f"  → {v['title'][:60]} (by {v['channel']})")
    else:
        warn(f"No videos directly mention '{name}'")

    if possible:
        info(f"  + {len(possible)} possibly related videos")
        for v in possible[:3]:
            info(f"  → {v['title'][:60]} (by {v['channel']})")

    # Channel search
    ch_resp = await client.get("https://www.googleapis.com/youtube/v3/search", params={
        "part": "snippet", "q": name, "type": "channel",
        "maxResults": 3, "key": YOUTUBE_KEY,
    })
    ch_data = ch_resp.json()
    has_channel = False
    for item in ch_data.get("items", []):
        ch_name = item.get("snippet", {}).get("title", "")
        if name_lower in ch_name.lower():
            has_channel = True
            ok(f"Own YouTube channel found: {ch_name}")
            break

    if not has_channel:
        fail("No dedicated YouTube channel found")


# ─── AI Readiness Check ─────────────────────────────────────────────────────

async def check_ai_readiness(gm_data: dict, website_data: dict, la_mentions: int):
    header("AI READINESS (computed)")

    if not website_data:
        fail("No website data — can't check")
        return

    html = website_data.get("html", "")
    md = website_data.get("md", "")

    # Schema
    has_schema = 'application/ld+json' in html or "schema.org" in md
    if has_schema:
        ok("Schema markup present (checked HTML)")
    else:
        fail("No Schema markup")

    # Review keywords
    reviews = gm_data.get("reviews") if gm_data else 0
    if reviews and reviews >= 50:
        ok(f"{reviews} reviews (50+ ✓) — likely contains product keywords")
    else:
        fail(f"{reviews or 0} reviews (need 50+ for keyword signal)")

    # NAP consistency
    gm_title = (gm_data.get("title", "") if gm_data else "").lower()
    web_title = (website_data.get("meta", {}).get("title", "")).lower()
    if gm_title and web_title and (gm_title in web_title or web_title in gm_title):
        ok(f"NAP consistent: Maps='{gm_title[:30]}' Website='{web_title[:30]}'")
    else:
        fail(f"NAP mismatch: Maps='{gm_title[:30]}' Website='{web_title[:30]}'")

    # Local mentions
    if la_mentions >= 3:
        ok(f"{la_mentions} local mentions (3+ ✓)")
    else:
        fail(f"{la_mentions} local mentions (need 3+)")


# ─── Summary ─────────────────────────────────────────────────────────────────

def summary():
    header("KNOWN ISSUES WITH OUR CHECKS")
    print("""
  1. SCHEMA CHECK IS BROKEN
     We check markdown for "schema.org" — but Firecrawl strips <script> tags.
     FIX: Request rawHtml and check for 'application/ld+json'.

  2. LINKS CHECK IS BROKEN
     Firecrawl returns 0 links for JS-heavy sites (React, Next.js).
     FIX: Parse links from rawHtml as fallback.

  3. REVIEW KEYWORDS IS FAKE
     We just check if review count >= 50, not actual keyword content.
     FIX: Use SerpApi Reviews API to analyze actual review text.

  4. BLOG CHECK IS WEAK
     We only check if "blog" appears in markdown or links.
     FIX: Check rawHtml, or try fetching /blog path directly.

  5. CONTENT CHECK IS SURFACE-LEVEL
     We only check character count. A page with 38K chars of cookie
     banners and footer text scores the same as 38K of real content.
     FIX: Use AI to assess content quality, not just length.
""")


# ─── Main ────────────────────────────────────────────────────────────────────

async def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/audit_test.py <business_name> <city> [website_url]")
        print("Example: python scripts/audit_test.py 'Baran Bistro' 'Berlin' 'https://baranbistro.com'")
        sys.exit(1)

    name = sys.argv[1]
    city = sys.argv[2]
    url = sys.argv[3] if len(sys.argv) > 3 else ""

    print(f"\n🔍 Auditing: {name} in {city}")
    if url:
        print(f"   Website: {url}")
    print(f"   APIs: SerpApi={'✓' if SERPAPI_KEY else '✗'} Firecrawl={'✓' if FIRECRAWL_KEY else '✗'} YouTube={'✓' if YOUTUBE_KEY else '✗'}")

    gm_data = await check_google_maps(name, city)
    website_data = await check_website(url) if url else None
    await check_local_authority(name, city)
    await check_youtube(name, city)

    la_mentions = 0  # Would come from local authority check
    await check_ai_readiness(gm_data or {}, website_data or {}, la_mentions)

    summary()

    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
