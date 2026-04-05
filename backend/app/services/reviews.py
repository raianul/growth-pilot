import logging

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)


async def _get_data_id(place_id: str) -> str | None:
    """Get Google Maps data_id from place_id via a Maps search."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(
            "https://serpapi.com/search",
            params={
                "engine": "google_maps",
                "place_id": place_id,
                "api_key": settings.serpapi_key,
            },
        )
    response.raise_for_status()
    data = response.json()
    return data.get("place_results", {}).get("data_id")


def _parse_reviews(data: dict) -> list[dict]:
    """Parse reviews from SerpApi response."""
    reviews = []
    for r in data.get("reviews", []):
        reviews.append({
            "text": r.get("snippet", r.get("text", "")),
            "rating": r.get("rating"),
            "author": r.get("user", {}).get("name", ""),
            "date": r.get("date", ""),
            "response": r.get("response", {}).get("snippet", ""),
        })
    return reviews


async def fetch_google_reviews(place_id: str) -> list[dict]:
    """Fetch recent Google Maps reviews for a place.

    Returns list of: {text, rating, author, date, response}
    Returns empty list (not None) so callers can iterate safely.
    Sets review["error"] sentinel if the fetch failed.
    """
    if not place_id or not settings.serpapi_key:
        return []

    try:
        # Step 1: Get data_id from place_id
        data_id = await _get_data_id(place_id)
        if not data_id:
            logger.warning("Could not get data_id for place_id %s", place_id)
            return [{"_error": "could_not_check", "text": "", "rating": None, "author": "", "date": "", "response": ""}]

        # Step 2: Fetch reviews using data_id
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://serpapi.com/search",
                params={
                    "engine": "google_maps_reviews",
                    "data_id": data_id,
                    "api_key": settings.serpapi_key,
                    "hl": "en",
                    "sort_by": "newestFirst",
                },
            )
        response.raise_for_status()
        data = response.json()

        reviews = _parse_reviews(data)
        logger.info("Fetched %d reviews for place_id %s", len(reviews), place_id)
        return reviews
    except Exception as e:
        logger.error("Failed to fetch reviews for place_id %s: %s", place_id, e)
        return [{"_error": str(e), "text": "", "rating": None, "author": "", "date": "", "response": ""}]


async def fetch_google_reviews_by_place_id(place_id: str) -> list[dict]:
    """Fetch reviews using place_id directly (no data_id lookup).

    SerpApi accepts place_id for the google_maps_reviews engine.
    Saves 1 API call compared to fetch_google_reviews().
    """
    if not place_id or not settings.serpapi_key:
        return []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                "https://serpapi.com/search",
                params={
                    "engine": "google_maps_reviews",
                    "place_id": place_id,
                    "api_key": settings.serpapi_key,
                    "hl": "en",
                    "sort_by": "newestFirst",
                },
            )
        response.raise_for_status()
        data = response.json()

        reviews = _parse_reviews(data)
        logger.info("Fetched %d reviews for place_id %s (direct)", len(reviews), place_id)
        return reviews
    except Exception as e:
        logger.error("Failed to fetch reviews for place_id %s: %s", place_id, e)
        return [{"_error": str(e), "text": "", "rating": None, "author": "", "date": "", "response": ""}]
