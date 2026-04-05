#!/usr/bin/env python3
"""
Ground Truth Validation Script

Tests our audit checks against known businesses and validates:
1. Are we saying things that are TRUE?
2. Are we missing things that ARE TRUE?
3. Are we saying things that are FALSE?

Usage:
    python scripts/ground_truth.py

This tests a mix of:
- Small local business (Baran Bistro)
- Medium chain (McFit)
- Large brand (IKEA)
- Business with no website
"""

import asyncio
import json
import re
import httpx

# Load keys from backend/.env
SERPAPI_KEY = ""
FIRECRAWL_KEY = ""
YOUTUBE_KEY = ""

try:
    with open("backend/.env") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            if k == "SERPAPI_KEY": SERPAPI_KEY = v
            elif k == "FIRECRAWL_API_KEY": FIRECRAWL_KEY = v
            elif k == "YOUTUBE_API_KEY": YOUTUBE_KEY = v
except FileNotFoundError:
    pass

client = httpx.AsyncClient(timeout=30.0)

# ─── Test Cases ──────────────────────────────────────────────────────────────

TEST_CASES = [
    {
        "name": "Baran Bistro",
        "city": "Berlin",
        "url": "https://baranbistro.com",
        "type": "small_local",
        # Known truth (manually verified)
        "truth": {
            "has_gmb": True,
            "rating_above_4": True,
            "reviews_above_50": True,
            "has_website": True,
            "has_schema": True,       # @type=Restaurant in ld+json
            "has_links": True,        # 43 internal links
            "has_meta_desc": True,
            "has_title": True,
            "has_blog": False,
            "has_youtube_channel": False,
            "videos_mention_business": True,  # Micha D Boss videos
            "has_local_mentions": True,
        }
    },
    {
        "name": "McFit",
        "city": "Berlin",
        "url": "https://www.mcfit.com",
        "type": "medium_chain",
        "truth": {
            "has_gmb": True,
            "rating_above_4": False,  # 3.9
            "reviews_above_50": True,
            "has_website": True,
            "has_schema": True,
            "has_links": True,        # 70 internal links
            "has_meta_desc": True,
            "has_title": True,
            "has_blog": True,         # blog reference in HTML
            "has_youtube_channel": True,
            "videos_mention_business": True,
            "has_local_mentions": True,
        }
    },
    {
        "name": "IKEA",
        "city": "Berlin",
        "url": "https://www.ikea.com/de/de/",
        "type": "large_brand",
        "truth": {
            "has_gmb": True,
            "rating_above_4": True,   # 4.0
            "reviews_above_50": True, # 17,040
            "has_website": True,
            "has_schema": True,       # @type=WebSite
            "has_links": True,        # 399 links
            "has_meta_desc": True,
            "has_title": True,
            "has_blog": False,        # Not obvious on homepage
            "has_youtube_channel": True,
            "videos_mention_business": True,
            "has_local_mentions": True,
        }
    },
]


# ─── Our Checks (simulating what the audit pipeline does) ────────────────────

async def run_our_checks(case: dict) -> dict:
    """Run the same checks our product runs and return what we'd report."""
    results = {}
    name = case["name"]
    city = case["city"]
    url = case["url"]

    # Google Maps
    if SERPAPI_KEY:
        resp = await client.get("https://serpapi.com/search", params={
            "engine": "google_maps", "q": f"{name} {city}", "api_key": SERPAPI_KEY,
        })
        data = resp.json()
        pr = data.get("place_results", {})
        lr = data.get("local_results", [])

        if pr:
            results["has_gmb"] = True
            results["rating_above_4"] = (pr.get("rating") or 0) >= 4.0
            results["reviews_above_50"] = (pr.get("reviews") or 0) >= 50
        elif lr:
            found = next((r for r in lr if name.lower() in r.get("title", "").lower()), None)
            results["has_gmb"] = found is not None
            if found:
                results["rating_above_4"] = (found.get("rating") or 0) >= 4.0
                results["reviews_above_50"] = (found.get("reviews") or 0) >= 50
            else:
                results["rating_above_4"] = False
                results["reviews_above_50"] = False
        else:
            results["has_gmb"] = False
            results["rating_above_4"] = False
            results["reviews_above_50"] = False

    # Website
    results["has_website"] = bool(url)

    if url and FIRECRAWL_KEY:
        resp = await client.post("https://api.firecrawl.dev/v1/scrape", headers={
            "Authorization": f"Bearer {FIRECRAWL_KEY}",
        }, json={"url": url, "formats": ["markdown", "rawHtml"]})
        data = resp.json()

        if data.get("success"):
            page = data.get("data", {})
            md = page.get("markdown", "")
            html = page.get("rawHtml", "")
            meta = page.get("metadata", {})
            links = page.get("links", [])

            results["has_meta_desc"] = bool(meta.get("description"))
            results["has_title"] = bool(meta.get("title"))

            # Links — check HTML fallback
            if len(links) >= 3:
                results["has_links"] = True
            elif html:
                domain = url.split("//")[1].split("/")[0] if "//" in url else ""
                html_hrefs = re.findall(r'href="([^"]*)"', html)
                internal = [h for h in html_hrefs if h.startswith("/") or (domain and domain in h)]
                results["has_links"] = len(internal) >= 3
            else:
                results["has_links"] = False

            # Schema — check HTML
            if html and "application/ld+json" in html:
                results["has_schema"] = True
            elif "schema.org" in md or "LocalBusiness" in md:
                results["has_schema"] = True
            else:
                results["has_schema"] = False

            # Blog — check HTML
            if any("blog" in str(l).lower() for l in links):
                results["has_blog"] = True
            elif html and re.search(r'href="[^"]*blog[^"]*"', html, re.IGNORECASE):
                results["has_blog"] = True
            else:
                results["has_blog"] = False
        else:
            for k in ["has_meta_desc", "has_title", "has_links", "has_schema", "has_blog"]:
                results[k] = False

    # YouTube
    if YOUTUBE_KEY:
        resp = await client.get("https://www.googleapis.com/youtube/v3/search", params={
            "part": "snippet", "q": f"{name} {city}", "type": "video",
            "maxResults": 10, "key": YOUTUBE_KEY,
        })
        data = resp.json()
        name_lower = name.lower()
        confirmed = [i for i in data.get("items", [])
                     if name_lower in (i.get("snippet", {}).get("title", "") + i.get("snippet", {}).get("description", "")).lower()]
        results["videos_mention_business"] = len(confirmed) > 0

        # Channel
        ch_resp = await client.get("https://www.googleapis.com/youtube/v3/search", params={
            "part": "snippet", "q": name, "type": "channel",
            "maxResults": 3, "key": YOUTUBE_KEY,
        })
        ch_data = ch_resp.json()
        results["has_youtube_channel"] = any(
            name_lower in i.get("snippet", {}).get("title", "").lower()
            for i in ch_data.get("items", [])
        )

    # Local Authority
    if SERPAPI_KEY:
        mentions = 0
        for query in [f"{name} {city} best", f"{name} review blog"]:
            resp = await client.get("https://serpapi.com/search", params={
                "engine": "google", "q": query, "api_key": SERPAPI_KEY, "num": 10,
            })
            data = resp.json()
            for r in data.get("organic_results", []):
                if name.lower() in (r.get("title", "") + r.get("snippet", "")).lower():
                    mentions += 1
        results["has_local_mentions"] = mentions >= 1

    return results


# ─── Validation ──────────────────────────────────────────────────────────────

def compare(truth: dict, our_result: dict, case_name: str) -> dict:
    """Compare ground truth vs our checks."""
    correct = 0
    false_positive = 0  # We say YES but truth is NO
    false_negative = 0  # We say NO but truth is YES
    missing = 0
    details = []

    for key, expected in truth.items():
        if key not in our_result:
            missing += 1
            details.append(f"  ⬜ {key}: not checked")
            continue

        actual = our_result[key]
        if actual == expected:
            correct += 1
            symbol = "✅" if expected else "✅"
            details.append(f"  ✅ {key}: correct ({actual})")
        elif actual and not expected:
            false_positive += 1
            details.append(f"  🔴 {key}: FALSE POSITIVE — we say YES, truth is NO")
        else:
            false_negative += 1
            details.append(f"  🟡 {key}: FALSE NEGATIVE — we say NO, truth is YES")

    total = correct + false_positive + false_negative + missing
    accuracy = (correct / total * 100) if total > 0 else 0

    return {
        "case": case_name,
        "correct": correct,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "missing": missing,
        "total": total,
        "accuracy": accuracy,
        "details": details,
    }


# ─── Main ────────────────────────────────────────────────────────────────────

async def main():
    print("🔬 Ground Truth Validation")
    print(f"   APIs: SerpApi={'✓' if SERPAPI_KEY else '✗'} Firecrawl={'✓' if FIRECRAWL_KEY else '✗'} YouTube={'✓' if YOUTUBE_KEY else '✗'}")

    all_results = []

    for case in TEST_CASES:
        print(f"\n{'='*60}")
        print(f"  Testing: {case['name']} ({case['type']})")
        print(f"{'='*60}")

        our_result = await run_our_checks(case)
        comparison = compare(case["truth"], our_result, case["name"])
        all_results.append(comparison)

        for line in comparison["details"]:
            print(line)

        print(f"\n  Accuracy: {comparison['accuracy']:.0f}% ({comparison['correct']}/{comparison['total']})")
        if comparison["false_positive"]:
            print(f"  🔴 False positives: {comparison['false_positive']} (we say something's fine when it's NOT)")
        if comparison["false_negative"]:
            print(f"  🟡 False negatives: {comparison['false_negative']} (we say something's wrong when it's FINE)")

    # Summary
    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")

    total_correct = sum(r["correct"] for r in all_results)
    total_fp = sum(r["false_positive"] for r in all_results)
    total_fn = sum(r["false_negative"] for r in all_results)
    total_missing = sum(r["missing"] for r in all_results)
    total_checks = sum(r["total"] for r in all_results)
    overall_accuracy = (total_correct / total_checks * 100) if total_checks > 0 else 0

    print(f"\n  Overall accuracy: {overall_accuracy:.0f}% ({total_correct}/{total_checks})")
    print(f"  ✅ Correct: {total_correct}")
    print(f"  🔴 False positives: {total_fp}")
    print(f"  🟡 False negatives: {total_fn}")
    print(f"  ⬜ Not checked: {total_missing}")

    if total_fn > 0:
        print(f"\n  ⚠️  FALSE NEGATIVES are the worst — we tell the user something")
        print(f"     is broken when it's actually fine. This destroys trust.")

    if total_fp > 0:
        print(f"\n  ⚠️  FALSE POSITIVES mean we miss real problems.")
        print(f"     Less urgent but reduces product value.")

    print(f"\n  RULES WE SHOULD FOLLOW:")
    print(f"  1. Never say 'No Schema' without checking HTML (not just markdown)")
    print(f"  2. Never say '0 links' without parsing HTML as fallback")
    print(f"  3. Never say 'Launch a website' if the user provided a URL")
    print(f"  4. Never show a score number — show plain language status")
    print(f"  5. If a check fails technically (API error), say 'Could not check' not 'Missing'")
    print(f"  6. If data is stale, clearly label it and don't present as current")
    print(f"  7. Review keywords: check actual review text, not just count >= 50")
    print(f"  8. Content quality: use AI to assess, not just char count")

    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
