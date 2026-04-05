import logging

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

SERPAPI_BASE = "https://serpapi.com/search"


async def fetch_google_maps_data(business_name: str, city: str, category: str) -> dict:
    """Fetch Google Maps data for a specific business."""
    if settings.dev_mode and not settings.serpapi_key:
        from app.services.mock import mock_google_maps
        return mock_google_maps(business_name, city, category)

    try:
        params = {
            "engine": "google_maps",
            "q": f"{business_name} {category} {city}",
            "api_key": settings.serpapi_key,
            "type": "search",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(SERPAPI_BASE, params=params)
        response.raise_for_status()
        data = response.json()

        # Check direct place match first (when Google Maps returns a single result)
        place = data.get("place_results")
        if place and business_name.lower() in place.get("title", "").lower():
            return {
                "place_id": place.get("place_id"),
                "position": 1,  # Direct match = top result
                "rating": place.get("rating"),
                "reviews": place.get("reviews"),
                "title": place.get("title"),
                "error": None,
            }

        # Then check local results list
        results = data.get("local_results", [])
        for result in results:
            if business_name.lower() in result.get("title", "").lower():
                return {
                    "place_id": result.get("place_id"),
                    "position": result.get("position"),
                    "rating": result.get("rating"),
                    "reviews": result.get("reviews"),
                    "title": result.get("title"),
                    "error": None,
                }
        return {"place_id": None, "position": None, "rating": None, "reviews": None, "title": business_name, "error": None}
    except Exception as e:
        logger.error("Failed to fetch Google Maps data for %s: %s", business_name, e)
        return {
            "place_id": None,
            "position": None,
            "rating": None,  # None = could not check
            "reviews": None,
            "title": business_name,
            "error": str(e),
        }


async def discover_competitors(
    business_name: str, city: str, category: str,
    exclude_place_id: str | None = None, max_competitors: int = 3,
) -> list[dict]:
    """Find top competitors in the same category and city."""
    if settings.dev_mode and not settings.serpapi_key:
        from app.services.mock import mock_competitors
        return mock_competitors(business_name, city, category)

    try:
        params = {
            "engine": "google_maps",
            "q": f"{category} {city}",
            "api_key": settings.serpapi_key,
            "type": "search",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(SERPAPI_BASE, params=params)
        response.raise_for_status()
        data = response.json()

        results = data.get("local_results", [])
        competitors = []
        for result in results:
            place_id = result.get("place_id")
            if place_id == exclude_place_id:
                continue
            competitors.append({
                "place_id": place_id,
                "business_name": result.get("title"),
                "rating": result.get("rating"),
                "reviews": result.get("reviews"),
                "position": result.get("position"),
            })
            if len(competitors) >= max_competitors:
                break
        return competitors
    except Exception as e:
        logger.error("Failed to discover competitors for %s in %s: %s", business_name, city, e)
        return []


async def discover_nearby_restaurants(
    lat: str, lng: str,
    exclude_place_id: str | None = None,
    max_results: int = 10,
) -> list[dict]:
    """Discover restaurants near a location using SerpApi Google Maps search.

    One API call returns up to 20 results with rating, reviews, etc.
    """
    if not settings.serpapi_key:
        return []

    try:
        params = {
            "engine": "google_maps",
            "q": "restaurant",
            "ll": f"@{lat},{lng},15z",
            "api_key": settings.serpapi_key,
            "type": "search",
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(SERPAPI_BASE, params=params)
        response.raise_for_status()
        data = response.json()

        results = data.get("local_results", [])
        competitors = []
        for r in results:
            pid = r.get("place_id")
            if pid == exclude_place_id:
                continue
            gps = r.get("gps_coordinates") or {}
            competitors.append({
                "place_id": pid,
                "business_name": r.get("title", ""),
                "rating": r.get("rating"),
                "reviews": r.get("reviews"),
                "address": r.get("address", ""),
                "types": r.get("type", r.get("types", "")),
                "thumbnail": r.get("thumbnail"),
                "lat": gps.get("latitude"),
                "lng": gps.get("longitude"),
            })
            if len(competitors) >= max_results:
                break
        return competitors
    except Exception as e:
        logger.error("Failed to discover nearby restaurants at %s,%s: %s", lat, lng, e)
        return []


async def fetch_place_details(place_id: str) -> dict | None:
    """Fetch detailed place info by place_id. Returns website, phone, hours, description.

    One SerpApi call. Used as a fallback when crawler data is missing website URL.
    """
    if not settings.serpapi_key:
        return None

    try:
        params = {
            "engine": "google_maps",
            "place_id": place_id,
            "api_key": settings.serpapi_key,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(SERPAPI_BASE, params=params)
        response.raise_for_status()
        data = response.json()

        pr = data.get("place_results", {})
        if not pr:
            return None

        return {
            "website": pr.get("website"),
            "menu_link": (pr.get("menu") or {}).get("link"),
            "phone": pr.get("phone"),
            "hours": pr.get("operating_hours"),
            "description": pr.get("description"),
        }
    except Exception as e:
        logger.error("Failed to fetch place details for %s: %s", place_id, e)
        return None
