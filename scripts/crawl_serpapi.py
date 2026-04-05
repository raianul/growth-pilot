"""
SerpAPI restaurant discovery for a postcode area.
Uses pagination (start=0,20,40,...) from a central point instead of multiple sector searches.

Usage:
    python scripts/crawl_serpapi.py --postcode 1230
    python scripts/crawl_serpapi.py --postcode 1230 --max-pages 3
"""

import requests
import json
import os
import time
import argparse
from datetime import datetime, timezone

SERPAPI_KEY = os.getenv("SERPAPI_API_KEY", "")

# Dhaka postcodes — one central coordinate per area
POSTCODES = {
    "1230": {"name": "Uttara", "lat": 23.8759, "lng": 90.3795},
    "1205": {"name": "Dhanmondi", "lat": 23.7461, "lng": 90.3742},
    "1212": {"name": "Gulshan", "lat": 23.7925, "lng": 90.4078},
    "1213": {"name": "Banani", "lat": 23.7937, "lng": 90.4030},
    "1209": {"name": "Mirpur", "lat": 23.8042, "lng": 90.3687},
}


import math

def _distance_km(lat1, lng1, lat2, lng2):
    """Haversine distance in km between two coordinates."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

MAX_DISTANCE_KM = 5


def search_page(lat, lng, start=0):
    """Search one page of SerpAPI Google Maps results."""
    params = {
        "engine": "google_maps",
        "q": "places to eat",
        "ll": f"@{lat},{lng},14z",
        "type": "search",
        "api_key": SERPAPI_KEY,
        "hl": "en",
        "start": start,
        "nearby": "1",
    }

    response = requests.get("https://serpapi.com/search", params=params)
    data = response.json()

    if "error" in data:
        print(f"  SerpAPI error: {data['error']}")
        return []

    results = data.get("local_results", [])
    return results


def parse_restaurant(r):
    """Extract restaurant data from a SerpAPI result."""
    return {
        "business_name": r.get("title", ""),
        "google_place_id": r.get("place_id", ""),
        "data_id": r.get("data_id", ""),
        "rating": r.get("rating"),
        "review_count": r.get("reviews", 0),
        "address": r.get("address", ""),
        "lat": r.get("gps_coordinates", {}).get("latitude"),
        "lng": r.get("gps_coordinates", {}).get("longitude"),
        "categories": r.get("type", ""),
        "phone": r.get("phone", ""),
        "price_level": r.get("price", ""),
        "hours": r.get("hours", ""),
        "description": r.get("description", ""),
        "thumbnail": r.get("thumbnail", ""),
    }


def crawl_postcode(postcode, area, max_pages=6):
    """Crawl all pages for a postcode. Returns deduplicated list."""
    all_restaurants = {}

    for page in range(max_pages):
        start = page * 20
        print(f"  Page {page + 1} (start={start})...", end=" ")

        results = search_page(area["lat"], area["lng"], start=start)
        if not results:
            print("no results — done.")
            break

        new = 0
        skipped = 0
        for r in results:
            parsed = parse_restaurant(r)
            pid = parsed["google_place_id"]
            if not pid or pid in all_restaurants:
                continue
            # Filter out results too far from center
            if parsed["lat"] and parsed["lng"]:
                dist = _distance_km(area["lat"], area["lng"], parsed["lat"], parsed["lng"])
                if dist > MAX_DISTANCE_KM:
                    skipped += 1
                    continue
            all_restaurants[pid] = parsed
            new += 1

        msg = f"{len(results)} results, {new} new"
        if skipped:
            msg += f", {skipped} too far"
        msg += f" (total: {len(all_restaurants)})"
        print(msg)

        if len(results) < 20:
            print("  Last page reached.")
            break

        time.sleep(1)

    return list(all_restaurants.values())


def main():
    parser = argparse.ArgumentParser(description="Crawl restaurants for a postcode via SerpAPI")
    parser.add_argument("--postcode", required=True, help="Postcode to crawl (e.g. 1230)")
    parser.add_argument("--max-pages", type=int, default=6, help="Max pages to fetch (20 results each, default 6 = 120 max)")
    args = parser.parse_args()

    postcode = args.postcode

    if postcode not in POSTCODES:
        print(f"Unknown postcode: {postcode}")
        print(f"Available: {', '.join(POSTCODES.keys())}")
        return

    area = POSTCODES[postcode]

    # Check if already crawled
    out_dir = f"data/crawl/{postcode}"
    filepath = f"{out_dir}/serpapi.json"

    if os.path.exists(filepath):
        with open(filepath) as f:
            existing = json.load(f)
        print(f"Already crawled: {filepath}")
        print(f"  {existing['total_found']} restaurants from {existing['crawled_at']}")
        print(f"  Delete the file to re-crawl.")
        return

    # Crawl
    print(f"Crawling {area['name']} (postcode {postcode})...")
    print(f"  Center: {area['lat']}, {area['lng']}")
    print(f"  Max pages: {args.max_pages} ({args.max_pages * 20} results max)\n")

    restaurants = crawl_postcode(postcode, area, max_pages=args.max_pages)

    # Save
    output = {
        "postcode": postcode,
        "area_name": area["name"],
        "coordinates": {"lat": area["lat"], "lng": area["lng"]},
        "crawled_at": datetime.now(timezone.utc).isoformat(),
        "pages_fetched": min(args.max_pages, (len(restaurants) // 20) + 1),
        "total_found": len(restaurants),
        "restaurants": restaurants,
    }

    os.makedirs(out_dir, exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to {filepath}")
    print(f"\nSummary:")
    print(f"  Area: {area['name']} ({postcode})")
    print(f"  Unique restaurants: {len(restaurants)}")

    if restaurants:
        rated = [r for r in restaurants if r["rating"]]
        avg_rating = sum(r["rating"] for r in rated) / len(rated) if rated else 0
        avg_reviews = sum(r["review_count"] for r in restaurants) / len(restaurants)
        print(f"  Average rating: {avg_rating:.1f}★")
        print(f"  Average reviews: {avg_reviews:.0f}")
        print(f"\n  Top 10 by reviews:")
        for r in sorted(restaurants, key=lambda x: x["review_count"], reverse=True)[:10]:
            print(f"    {r['business_name']} — {r['rating']}★, {r['review_count']} reviews")


if __name__ == "__main__":
    main()
