import re

import httpx

from app.core.config import settings


def _make_client() -> httpx.AsyncClient:
    """Create a fresh httpx client per call to avoid event loop conflicts in Celery."""
    return httpx.AsyncClient(
        timeout=15.0,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0"},
    )


async def resolve_maps_link(maps_url: str) -> dict:
    """Resolve a Google Maps link and return business details via SerpApi."""

    async with _make_client() as client:
        # Step 1: Resolve short URL to full URL
        full_url = maps_url
        if "maps.app.goo.gl" in maps_url or "goo.gl" in maps_url:
            resp = await client.head(maps_url, follow_redirects=True)
            full_url = str(resp.url)

        # Step 2: Extract place name and coordinates from URL
        # URL format: /maps/place/Place+Name/@lat,lng,zoom
        name_match = re.search(r"/place/([^/@]+)", full_url)
        coord_match = re.search(r"@([-\d.]+),([-\d.]+)", full_url)

        place_name = ""
        if name_match:
            place_name = name_match.group(1).replace("+", " ")

        lat, lng = None, None
        if coord_match:
            lat = coord_match.group(1)
            lng = coord_match.group(2)

        if not place_name:
            return {"error": "Could not extract business name from URL"}

        # Step 3: Search SerpApi with name + coordinates
        params: dict = {
            "engine": "google_maps",
            "q": place_name,
            "api_key": settings.serpapi_key,
        }
        if lat and lng:
            params["ll"] = f"@{lat},{lng},17z"

        resp = await client.get("https://serpapi.com/search", params=params)
        resp.raise_for_status()
        data = resp.json()

    # Check place_results first (direct match)
    pr = data.get("place_results", {})
    if pr:
        address = pr.get("address", "")
        city = _extract_city(address)

        types = pr.get("type", [])
        if isinstance(types, str):
            types = [types]

        category = _map_category(types)

        # Extract GPS from place_results if available
        gps = pr.get("gps_coordinates") or {}
        p_lat = gps.get("latitude") or lat
        p_lng = gps.get("longitude") or lng

        return {
            "business_name": pr.get("title", place_name),
            "rating": pr.get("rating"),
            "reviews": pr.get("reviews"),
            "place_id": pr.get("place_id"),
            "address": address,
            "city": city,
            "category": category,
            "types": types,
            "lat": p_lat,
            "lng": p_lng,
            "website": pr.get("website"),
            "menu_link": (pr.get("menu") or {}).get("link"),
            "phone": pr.get("phone"),
            "hours": pr.get("operating_hours"),
            "photos_count": pr.get("photos_count"),
            "description": pr.get("description"),
        }

    # Fallback to local_results
    results = data.get("local_results", [])
    if results:
        r = results[0]
        address = r.get("address", "")
        gps = r.get("gps_coordinates") or {}
        types = r.get("type", r.get("types", []))
        if isinstance(types, str):
            types = [types]
        return {
            "business_name": r.get("title", place_name),
            "rating": r.get("rating"),
            "reviews": r.get("reviews"),
            "place_id": r.get("place_id"),
            "address": address,
            "city": _extract_city(address),
            "category": _map_category(types),
            "types": types,
            "lat": gps.get("latitude") or lat,
            "lng": gps.get("longitude") or lng,
            "website": r.get("website"),
            "phone": r.get("phone"),
            "hours": None,
            "photos_count": None,
            "description": None,
        }

    return {
        "business_name": place_name,
        "rating": None,
        "reviews": None,
        "place_id": None,
        "address": None,
        "city": None,
        "category": None,
        "types": [],
        "lat": lat,
        "lng": lng,
    }


def _extract_city(address: str) -> str:
    """Extract city from a formatted address string."""
    if not address:
        return ""
    parts = [p.strip() for p in address.split(",")]
    for part in parts:
        # Look for German city pattern: optional postal code + city name
        city_match = re.search(r"(\d{5}\s+)?([A-Z][a-zäöüÄÖÜ]+)", part)
        if city_match:
            return city_match.group(2)
    return ""


def _map_category(types: list[str]) -> str:
    """Map Google Maps place types to our category values."""
    type_str = " ".join(types).lower()
    if any(w in type_str for w in ["restaurant", "food", "doner", "kebab", "pizza", "sushi"]):
        return "restaurant"
    if any(w in type_str for w in ["cafe", "coffee", "bakery", "pastry"]):
        return "cafe"
    if any(w in type_str for w in ["gym", "fitness", "sport"]):
        return "gym"
    if any(w in type_str for w in ["salon", "beauty", "hair", "spa"]):
        return "salon"
    if any(w in type_str for w in ["bar", "pub", "nightclub", "club"]):
        return "bar"
    if any(w in type_str for w in ["bakery", "bread", "pastry"]):
        return "bakery"
    if any(w in type_str for w in ["shop", "store", "retail", "boutique"]):
        return "retail"
    return "other"
