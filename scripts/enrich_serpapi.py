#!/usr/bin/env python3
"""
Enrich businesses with social profiles, delivery platform URLs, and directory listings
using SerpAPI Google Search.

Usage:
    cd backend && python ../scripts/enrich_serpapi.py --postcode 1230
    cd backend && python ../scripts/enrich_serpapi.py --postcode 1230 --min-reviews 20
    cd backend && python ../scripts/enrich_serpapi.py --postcode 1230 --limit 5
"""
import argparse
import asyncio
import difflib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select
from app.core.database import async_session
from app.models.business import Business

SERPAPI_KEY = os.getenv("SERPAPI_API_KEY", "")
SERPAPI_BASE = "https://serpapi.com/search"

DIRECTORY_DOMAINS = [
    "tripadvisor.com", "restaurantbd.com", "wanderlog.com", "reviewbangla.com",
    "kemon.com", "moumachi.com", "top10place.com", "bippermedia.com",
    "zomato.com", "yelp.com", "wheree.com", "wanderboat.ai",
]


async def search_business(name: str, retries: int = 3) -> dict | None:
    """Call SerpAPI Google Search for a business name. Retries on 429."""
    params = {
        "engine": "google",
        "q": name,
        "location": "Dhaka, Dhaka Division, Bangladesh",
        "google_domain": "google.com.bd",
        "hl": "en",
        "gl": "bd",
        "api_key": SERPAPI_KEY,
    }
    for attempt in range(retries):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(SERPAPI_BASE, params=params)
            if response.status_code == 429:
                wait = 5 * (attempt + 1)
                print(f"  Rate limited (429). Waiting {wait}s...")
                time.sleep(wait)
                continue
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt < retries - 1:
                wait = 5 * (attempt + 1)
                print(f"  Rate limited (429). Waiting {wait}s...")
                time.sleep(wait)
                continue
            print(f"  API error: {e}")
            return None
        except Exception as e:
            print(f"  API error: {e}")
            return None
    return None


def _extract_slug(url: str) -> str:
    """Extract the page slug from a social URL. E.g. 'facebook.com/madchefbd/' → 'madchefbd'."""
    try:
        path = urlparse(url).path.strip("/")
        # Remove common prefixes like 'p/', 'pages/', 'profile.php'
        for prefix in ("pages/", "p/", "profile.php"):
            if path.lower().startswith(prefix):
                path = path[len(prefix):]
        # Take the first segment
        slug = path.split("/")[0] if path else ""
        # Remove query params that leaked into path
        slug = slug.split("?")[0]
        return slug.lower()
    except Exception:
        return ""


def _match_score(slug: str, business_name: str) -> float:
    """Score how well a URL slug matches the business name. 0.0 to 1.0."""
    if not slug:
        return 0.0

    name_clean = re.sub(r"[^a-z0-9]", "", business_name.lower())

    # Purely numeric ID (e.g. facebook.com/271218260180326) — low score
    if slug.isdigit():
        return 0.1

    slug_clean = re.sub(r"[^a-z0-9]", "", slug)

    # Direct containment — strong match
    if name_clean in slug_clean or slug_clean in name_clean:
        return 1.0

    # Fuzzy match
    return difflib.SequenceMatcher(None, name_clean, slug_clean).ratio()


def _extract_followers(displayed_link: str) -> str | None:
    """Extract follower count string from displayed_link.

    Examples:
        '204K+ followers' → '204K+'
        '17.4K+ followers' → '17.4K+'
        '৩.১ লা জনের বেশি ফলোয়ার' → raw text preserved
    """
    if not displayed_link:
        return None

    # English pattern: "204K+ followers" or "1.2M followers"
    match = re.search(r"([\d,.]+[KkMm]?\+?)\s*[Ff]ollowers", displayed_link)
    if match:
        return match.group(1)

    # Bangla/other pattern: contains follower-like text
    if "ফলোয়ার" in displayed_link or "followers" in displayed_link.lower():
        return displayed_link.strip()

    return None


def _extract_followers_from_snippet(snippet: str, platform: str) -> str | None:
    """Extract follower/like count from organic result snippet text.

    Facebook snippets: '311392 likes · 4953 talking about this'
    Instagram snippets: '12.5K followers'
    """
    if not snippet:
        return None

    if platform == "facebook":
        # "311392 likes" or "311,392 likes"
        match = re.search(r"([\d,]+)\s+likes", snippet)
        if match:
            count = int(match.group(1).replace(",", ""))
            if count >= 1_000_000:
                formatted = f"{count / 1_000_000:.1f}".rstrip("0").rstrip(".")
                return f"{formatted}M+"
            if count >= 1_000:
                formatted = f"{count / 1_000:.1f}".rstrip("0").rstrip(".")
                return f"{formatted}K+"
            return str(count)

    if platform in ("instagram", "tiktok"):
        match = re.search(r"([\d,.]+[KkMm]?\+?)\s*[Ff]ollowers", snippet)
        if match:
            return match.group(1)

    return None


SOCIAL_PLATFORMS = {
    "facebook": "facebook.com",
    "instagram": "instagram.com",
    "tiktok": "tiktok.com",
}


def extract_social_smart(business_name: str, kg: dict, organic: list) -> dict:
    """Extract social URLs using smart matching across knowledge_graph and organic_results.

    For each platform, collects all candidate URLs, scores them against the business name,
    and picks the best match. Also extracts follower counts from displayed_link and snippets.
    """
    # Collect candidates per platform: list of (url, source, score, followers)
    candidates: dict[str, list] = {"facebook": [], "instagram": [], "tiktok": [], "youtube": []}

    # 1. From knowledge_graph.profiles
    for p in (kg.get("profiles") or []):
        name = (p.get("name") or "").lower()
        link = p.get("link")
        if not link:
            continue
        for platform, domain in SOCIAL_PLATFORMS.items():
            if platform in name or domain in link.lower():
                slug = _extract_slug(link)
                score = _match_score(slug, business_name)
                candidates[platform].append({
                    "url": link, "source": "knowledge_graph",
                    "match_score": round(score, 2), "followers": None,
                })
        if "youtube" in name:
            candidates["youtube"].append({
                "url": link, "source": "knowledge_graph",
                "match_score": 0.5, "followers": None,
            })

    # 2. From organic_results
    for r in organic:
        url = r.get("link", "")
        displayed_link = r.get("displayed_link") or ""
        snippet = r.get("snippet") or ""
        url_lower = url.lower()

        for platform, domain in SOCIAL_PLATFORMS.items():
            if domain not in url_lower:
                continue

            slug = _extract_slug(url)
            score = _match_score(slug, business_name)

            # Skip deep subpages (posts, photos, videos, reviews, menu)
            path = urlparse(url).path.strip("/")
            segments = [s for s in path.split("/") if s]
            if len(segments) > 2:
                continue

            # Extract followers from displayed_link or snippet
            followers = _extract_followers(displayed_link)
            if not followers:
                followers = _extract_followers_from_snippet(snippet, platform)

            candidates[platform].append({
                "url": url, "source": "organic_results",
                "match_score": round(score, 2), "followers": followers,
            })

        # YouTube channel/handle URLs
        if "youtube.com/channel" in url_lower or "youtube.com/@" in url_lower:
            slug = _extract_slug(url)
            score = _match_score(slug, business_name)
            candidates["youtube"].append({
                "url": url, "source": "organic_results",
                "match_score": round(score, 2), "followers": None,
            })

    # 3. Pick best URL per platform
    result = {
        "facebook_url": None, "instagram_url": None, "tiktok_url": None,
        "facebook_followers": None, "instagram_followers": None,
        "youtube_url": None,
        "social_verification": {},
    }

    platform_to_key = {
        "facebook": "facebook_url", "instagram": "instagram_url",
        "tiktok": "tiktok_url", "youtube": "youtube_url",
    }

    for platform, key in platform_to_key.items():
        cands = candidates[platform]
        if not cands:
            continue

        # Sort by match_score descending
        cands.sort(key=lambda c: c["match_score"], reverse=True)
        best = cands[0]
        result[key] = best["url"]

        # Followers — use from best match, or from any candidate that has it
        followers_key = f"{platform}_followers"
        if followers_key in result:
            if best["followers"]:
                result[followers_key] = best["followers"]
            else:
                for c in cands:
                    if c["followers"]:
                        result[followers_key] = c["followers"]
                        break

        # Verification metadata
        result["social_verification"][platform] = {
            "selected_url": best["url"],
            "selected_source": best["source"],
            "match_score": best["match_score"],
            "alternative_urls": [
                {"url": c["url"], "source": c["source"], "match_score": c["match_score"]}
                for c in cands[1:]
            ],
        }

    return result


def extract_from_organic(results: list) -> dict:
    """Extract delivery URLs, directory listings, and YouTube mentions from organic results."""
    data = {
        "foodpanda_url": None,
        "pathao_url": None,
        "directory_listings": [],
        "youtube_mentions": [],
    }

    seen_urls = set()

    for r in results:
        url = r.get("link", "")
        if url in seen_urls:
            continue
        seen_urls.add(url)

        domain = (r.get("displayed_link") or url).lower()

        # Delivery platforms
        if "foodpanda.com.bd" in domain and not data["foodpanda_url"]:
            data["foodpanda_url"] = url
            rich = (r.get("rich_snippet") or {}).get("top", {}).get("detected_extensions", {})
            if rich:
                data["foodpanda_rating"] = rich.get("rating")
                data["foodpanda_reviews"] = rich.get("reviews")
        elif "pathao" in domain and not data["pathao_url"]:
            data["pathao_url"] = url

        # YouTube mentions (video links, not channel pages)
        elif "youtube.com" in domain and "/channel" not in url and "/@" not in url:
            data["youtube_mentions"].append({
                "title": r.get("title", ""),
                "url": url,
            })

        # Directory listings
        else:
            for dd in DIRECTORY_DOMAINS:
                if dd in domain:
                    rich = (r.get("rich_snippet") or {}).get("top", {}).get("detected_extensions", {})
                    data["directory_listings"].append({
                        "source": dd.split(".")[0],
                        "url": url,
                        "title": r.get("title", ""),
                        "rating": rich.get("rating"),
                        "reviews": rich.get("reviews"),
                    })
                    break

    return data


def parse_response(data: dict, business_name: str = "") -> dict:
    """Parse the full SerpAPI response into structured enrichment data."""
    kg = data.get("knowledge_graph") or {}
    organic = data.get("organic_results") or []
    menu_highlights = data.get("menu_highlights") or []

    # Smart social extraction — scores URLs against business name
    social = extract_social_smart(business_name, kg, organic)
    website_url = kg.get("website")

    kg_metadata = {}
    if kg.get("price_details"):
        kg_metadata["price_details"] = kg["price_details"]
    if kg.get("merchant_description"):
        kg_metadata["merchant_description"] = kg["merchant_description"]
    if kg.get("popular_times"):
        kg_metadata["popular_times"] = kg["popular_times"]
    if menu_highlights:
        # Filter out generic section headers and deduplicate
        skip_titles = {"price", "prices", "menu", "popular", "most popular", "top picks", "categories", "all"}
        seen = set()
        filtered_menu = []
        for m in menu_highlights:
            title = (m.get("title") or "").strip()
            if not title or title.lower() in skip_titles or title.lower() in seen:
                continue
            seen.add(title.lower())
            filtered_menu.append({"title": title, "price": m.get("price")})
            if len(filtered_menu) >= 8:
                break
        if filtered_menu:
            kg_metadata["menu_highlights"] = filtered_menu
    if kg.get("hours"):
        kg_metadata["hours_structured"] = kg["hours"]

    # From organic results
    organic_data = extract_from_organic(organic)

    return {
        "website_url": website_url,
        **social,
        "has_knowledge_graph": bool(kg),
        "kg_metadata": kg_metadata,
        "organic_data": organic_data,
    }


def _print_social_summary(parsed: dict) -> None:
    """Print a summary of social extraction results."""
    verification = parsed.get("social_verification") or {}

    for platform in ("facebook", "instagram", "tiktok", "youtube"):
        key = f"{platform}_url"
        url = parsed.get(key)
        v = verification.get(platform, {})
        score = v.get("match_score", "")
        source = v.get("selected_source", "")
        alts = len(v.get("alternative_urls", []))

        if url:
            clean = url.replace("https://", "").replace("http://", "")[:50]
            parts = [f"  {platform}: {clean}"]
            if score:
                parts.append(f"(score={score}, src={source})")
            if alts:
                parts.append(f"[+{alts} alt]")
            print(" ".join(parts))
        else:
            print(f"  {platform}: not found")

    # Followers
    for platform in ("facebook", "instagram"):
        followers = parsed.get(f"{platform}_followers")
        if followers:
            print(f"  {platform} followers: {followers}")

    # Website
    w = parsed.get("website_url")
    print(f"  website: {w.replace('https://', '').replace('http://', '')[:50] if w else 'not found'}")


async def enrich_business(biz: Business, parsed: dict, raw_response: dict) -> None:
    """Update a single business record with enrichment data."""
    now = datetime.now(timezone.utc)

    async with async_session() as session:
        result = await session.execute(
            select(Business).where(Business.id == biz.id)
        )
        b = result.scalar_one()

        # Update social URLs — fill nulls, or upgrade if new URL has higher match score
        if not b.website_url and parsed["website_url"]:
            b.website_url = parsed["website_url"]

        verification = parsed.get("social_verification") or {}
        for platform, col in [("facebook", "facebook_url"), ("instagram", "instagram_url"), ("tiktok", "tiktok_url")]:
            new_url = parsed.get(f"{platform}_url")
            if not new_url:
                continue
            existing = getattr(b, col)
            if not existing:
                setattr(b, col, new_url)
            elif existing != new_url:
                # Replace if new URL has a better match score
                v = verification.get(platform, {})
                new_score = v.get("match_score", 0)
                old_slug = _extract_slug(existing)
                old_score = _match_score(old_slug, biz.business_name)
                if new_score > old_score:
                    setattr(b, col, new_url)

        # Merge into metadata (don't overwrite existing keys)
        existing_meta = dict(b.meta_data or {})
        organic = parsed["organic_data"]

        new_meta = {}
        if parsed["kg_metadata"]:
            for k, v in parsed["kg_metadata"].items():
                if k not in existing_meta:
                    new_meta[k] = v
        if organic.get("foodpanda_url"):
            new_meta.setdefault("foodpanda_url", organic["foodpanda_url"])
            if organic.get("foodpanda_rating"):
                new_meta.setdefault("foodpanda_rating", organic["foodpanda_rating"])
            if organic.get("foodpanda_reviews"):
                new_meta.setdefault("foodpanda_reviews", organic["foodpanda_reviews"])
        if organic.get("pathao_url"):
            new_meta.setdefault("pathao_url", organic["pathao_url"])
        # These fields should always overwrite (not setdefault) since re-enrichment should refresh them
        if organic.get("directory_listings"):
            new_meta["directory_listings"] = organic["directory_listings"]
        if organic.get("youtube_mentions"):
            new_meta["youtube_mentions"] = organic["youtube_mentions"]
        # Social followers + verification from smart extraction (always overwrite on re-enrich)
        if parsed.get("facebook_followers"):
            new_meta["facebook_followers"] = parsed["facebook_followers"]
        if parsed.get("instagram_followers"):
            new_meta["instagram_followers"] = parsed["instagram_followers"]
        if parsed.get("youtube_url"):
            new_meta["youtube_url"] = parsed["youtube_url"]
        if parsed.get("social_verification"):
            new_meta["social_verification"] = parsed["social_verification"]

        b.meta_data = {**existing_meta, **new_meta}

        # Store raw response
        existing_cached = dict(b.cached_data or {})
        existing_cached["google_search_raw"] = raw_response
        b.cached_data = existing_cached

        b.enriched = True
        b.enriched_at = now
        b.updated_at = now

        await session.commit()


async def run_single(place_id: str) -> None:
    """Re-enrich a single business by google_place_id, ignoring enriched flag."""
    async with async_session() as session:
        result = await session.execute(
            select(Business).where(Business.google_place_id == place_id)
        )
        biz = result.scalar_one_or_none()

    if not biz:
        print(f"Business not found: {place_id}")
        return

    print(f"Re-enriching: {biz.business_name} ({biz.review_count:,} reviews)\n")

    raw = await search_business(biz.business_name)
    if raw is None:
        print("API error — aborted.")
        return

    parsed = parse_response(raw, biz.business_name)

    _print_social_summary(parsed)

    organic = parsed["organic_data"]
    print(f"  foodpanda: {'found' if organic['foodpanda_url'] else 'not found'}")

    await enrich_business(biz, parsed, raw)
    print("  Saved.")


async def run(postcode: str, min_reviews: int, limit: int | None) -> None:
    # Fetch qualifying businesses
    async with async_session() as session:
        query = (
            select(Business)
            .where(
                Business.postcode == postcode,
                Business.enriched == False,
                Business.review_count >= min_reviews,
            )
            .order_by(Business.review_count.desc())
        )
        if limit:
            query = query.limit(limit)

        result = await session.execute(query)
        businesses = result.scalars().all()

    if not businesses:
        print(f"No businesses to enrich for postcode {postcode} (min {min_reviews} reviews)")
        return

    total = len(businesses)
    print(f"Enriching businesses in postcode {postcode} ({total} qualify, min {min_reviews} reviews)\n")

    stats = {
        "enriched": 0, "failed": 0,
        "website": 0, "facebook": 0, "instagram": 0, "tiktok": 0, "foodpanda": 0,
    }
    start_time = time.time()

    for i, biz in enumerate(businesses, 1):
        print(f"[{i}/{total}] {biz.business_name} ({biz.review_count:,} reviews)...")

        raw = await search_business(biz.business_name)
        if raw is None:
            print("  Skipped (API error)")
            stats["failed"] += 1
            time.sleep(2)
            continue

        parsed = parse_response(raw, biz.business_name)

        _print_social_summary(parsed)

        organic = parsed["organic_data"]
        print(f"  foodpanda: {'found' if organic['foodpanda_url'] else 'not found'}")
        if organic["directory_listings"]:
            print(f"  directories: {len(organic['directory_listings'])} found")
        if organic["youtube_mentions"]:
            print(f"  youtube: {len(organic['youtube_mentions'])} mention(s)")

        # Save
        try:
            await enrich_business(biz, parsed, raw)
            print("  Saved.")
            stats["enriched"] += 1

            # Count what was filled
            if parsed["website_url"] or biz.website_url:
                stats["website"] += 1
            if parsed["facebook_url"] or biz.facebook_url:
                stats["facebook"] += 1
            if parsed["instagram_url"] or biz.instagram_url:
                stats["instagram"] += 1
            if parsed["tiktok_url"] or biz.tiktok_url:
                stats["tiktok"] += 1
            if organic["foodpanda_url"]:
                stats["foodpanda"] += 1
        except Exception as e:
            print(f"  Save failed: {e}")
            stats["failed"] += 1

        print()

        if i < total:
            time.sleep(5)

    elapsed = time.time() - start_time
    cost = total * 0.005

    print(f"Summary:")
    print(f"  Total processed: {total}")
    print(f"  Enriched: {stats['enriched']}")
    print(f"  Failed: {stats['failed']}")
    print(f"  Website: {stats['website']}/{total}")
    print(f"  Facebook: {stats['facebook']}/{total}")
    print(f"  Instagram: {stats['instagram']}/{total}")
    print(f"  TikTok: {stats['tiktok']}/{total}")
    print(f"  Foodpanda: {stats['foodpanda']}/{total}")
    print(f"  Cost: ~${cost:.2f} ({total} x $0.005)")
    print(f"  Time: {int(elapsed // 60)}m {int(elapsed % 60)}s")


def main():
    parser = argparse.ArgumentParser(description="Enrich businesses with SerpAPI Google Search")
    parser.add_argument("--postcode", default=None, help="Postcode to enrich (batch mode)")
    parser.add_argument("--place-id", default=None, help="Re-enrich a single business by google_place_id")
    parser.add_argument("--min-reviews", type=int, default=20, help="Minimum review count (default 20)")
    parser.add_argument("--limit", type=int, default=None, help="Max businesses to process (for testing)")
    args = parser.parse_args()

    if args.place_id:
        asyncio.run(run_single(args.place_id))
    elif args.postcode:
        asyncio.run(run(args.postcode, args.min_reviews, args.limit))
    else:
        print("Provide either --postcode or --place-id")
        parser.print_help()


if __name__ == "__main__":
    main()
