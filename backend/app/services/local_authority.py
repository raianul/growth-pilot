import logging

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

SERPAPI_BASE = "https://serpapi.com/search"

TRUSTED_DOMAINS = {
    "yelp.com", "tripadvisor.com", "trustpilot.com", "google.com",
    "foursquare.com", "yellowpages.com", "bbb.org", "angi.com",
    "thumbtack.com", "houzz.com", "zomato.com", "opentable.com",
}


def _is_trusted_source(url: str) -> bool:
    """Check if a URL belongs to a trusted directory or review site."""
    url_lower = url.lower()
    return any(domain in url_lower for domain in TRUSTED_DOMAINS)


async def fetch_local_authority(business_name: str, city: str) -> dict:
    """
    Search Google for local mentions, best-of lists, and directory presence.

    Returns:
        {
            "mention_count": int,
            "sources": [{"title": str, "url": str, "snippet": str}],
            "on_best_of_list": bool,
        }
    """
    if settings.dev_mode and not settings.serpapi_key:
        from app.services.mock import mock_local_authority
        return mock_local_authority(business_name, city)

    try:
        return await _fetch_local_authority_inner(business_name, city)
    except Exception as e:
        logger.error("Failed to fetch local authority for %s: %s", business_name, e)
        return {
            "mention_count": None,  # None = could not check
            "sources": [],
            "on_best_of_list": None,
            "error": str(e),
        }


async def _fetch_local_authority_inner(business_name: str, city: str) -> dict:
    sources = []
    on_best_of_list = False

    for query in [f"{business_name} {city} best", f"{business_name} review blog"]:
        params = {
            "engine": "google",
            "q": query,
            "api_key": settings.serpapi_key,
            "num": 10,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(SERPAPI_BASE, params=params)
            response.raise_for_status()
            data = response.json()
        except Exception:
            continue

        organic = data.get("organic_results", [])
        for result in organic:
            title = result.get("title", "")
            url = result.get("link", "")
            snippet = result.get("snippet", "")

            # Check if this result mentions the business (all name words present)
            combined_text = (title + " " + snippet + " " + url).lower()
            name_words = [w for w in business_name.lower().split() if len(w) > 2]
            if not all(w in combined_text for w in name_words):
                continue

            # Extract domain for favicon
            domain = ""
            try:
                from urllib.parse import urlparse
                domain = urlparse(url).netloc
            except Exception:
                pass

            # Extract rich snippet data (rating, reviews, followers)
            rich = (result.get("rich_snippet") or {}).get("top", {}).get("detected_extensions", {})

            sources.append({
                "title": title,
                "url": url,
                "snippet": snippet,
                "date": result.get("date", ""),
                "domain": domain,
                "rating": rich.get("rating"),
                "reviews": rich.get("reviews"),
                "price_range": rich.get("price_range"),
            })

            # Detect "best of" list patterns
            if any(kw in title.lower() for kw in ["best", "top ", "ranked", "#1"]):
                on_best_of_list = True

    # Deduplicate by URL
    seen_urls: set[str] = set()
    unique_sources = []
    for s in sources:
        if s["url"] not in seen_urls:
            seen_urls.add(s["url"])
            unique_sources.append(s)

    return {
        "mention_count": len(unique_sources),
        "sources": unique_sources[:10],
        "on_best_of_list": on_best_of_list,
    }


async def fetch_local_authority_single(business_name: str, city: str) -> dict:
    """Single-search version of fetch_local_authority. Uses 1 SerpApi call instead of 2."""
    if settings.dev_mode and not settings.serpapi_key:
        from app.services.mock import mock_local_authority
        return mock_local_authority(business_name, city)

    try:
        return await _fetch_local_authority_single_inner(business_name, city)
    except Exception as e:
        logger.error("Failed to fetch local authority for %s: %s", business_name, e)
        return {
            "mention_count": None,
            "sources": [],
            "on_best_of_list": None,
            "error": str(e),
        }


async def _fetch_local_authority_single_inner(business_name: str, city: str) -> dict:
    sources = []
    on_best_of_list = False

    params = {
        "engine": "google",
        "q": f"{business_name} {city} best reviews blog",
        "api_key": settings.serpapi_key,
        "num": 10,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(SERPAPI_BASE, params=params)
    response.raise_for_status()
    data = response.json()

    organic = data.get("organic_results", [])
    for result in organic:
        title = result.get("title", "")
        url = result.get("link", "")
        snippet = result.get("snippet", "")

        if business_name.lower() not in (title + snippet).lower():
            continue

        domain = ""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
        except Exception:
            pass

        sources.append({
            "title": title,
            "url": url,
            "snippet": snippet,
            "date": result.get("date", ""),
            "domain": domain,
        })

        if any(kw in title.lower() for kw in ["best", "top ", "ranked", "#1"]):
            on_best_of_list = True

    seen_urls: set[str] = set()
    unique_sources = []
    for s in sources:
        if s["url"] not in seen_urls:
            seen_urls.add(s["url"])
            unique_sources.append(s)

    return {
        "mention_count": len(unique_sources),
        "sources": unique_sources[:10],
        "on_best_of_list": on_best_of_list,
    }
