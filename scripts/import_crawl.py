#!/usr/bin/env python3
"""
Import crawler JSON into the businesses table.

Usage:
    cd backend && python ../scripts/import_crawl.py --file ../data/crawl/1230/serpapi.json
"""
import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select
from app.core.database import async_session
from app.models.business import Business
from app.utils.slug import generate_unique_slug

# Bangladesh bounding box (roughly)
LAT_MIN, LAT_MAX = 23.0, 24.5
LNG_MIN, LNG_MAX = 89.5, 91.0


def _parse_timestamp(raw: str) -> datetime:
    if not raw or raw.lower() == "now":
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(raw)
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


async def run(filepath: str) -> None:
    with open(filepath, encoding="utf-8") as f:
        data = json.load(f)

    postcode = data.get("postcode", "")
    area_name = data.get("area_name", "")
    crawled_at = _parse_timestamp(data.get("crawled_at"))
    restaurants = data.get("restaurants", [])

    print(f"Importing {filepath}...")
    print(f"Postcode: {postcode} ({area_name})")
    print(f"Total in file: {len(restaurants)}")

    if not restaurants:
        print("No restaurants found in file.")
        return

    # Filter non-local
    local = []
    filtered_out = []
    for r in restaurants:
        lat = r.get("lat")
        lng = r.get("lng")
        if lat and lng and (lat < LAT_MIN or lat > LAT_MAX or lng < LNG_MIN or lng > LNG_MAX):
            filtered_out.append(r)
        else:
            local.append(r)

    if filtered_out:
        print(f"Filtered out (non-local): {len(filtered_out)}")
        print()
        for r in filtered_out:
            print(f"  {r.get('business_name')} (lat: {r.get('lat'):.2f}, lng: {r.get('lng'):.2f})")
        print()

    new_count = 0
    updated_count = 0
    skipped = 0

    async with async_session() as session:
        for r in local:
            pid = r.get("google_place_id")
            if not pid:
                skipped += 1
                continue

            result = await session.execute(
                select(Business).where(Business.google_place_id == pid)
            )
            existing = result.scalar_one_or_none()

            now = datetime.now(timezone.utc)

            # Metadata — display-only fields, not duplicated in columns
            meta = {}
            if r.get("phone"):
                meta["phone"] = r["phone"]
            if r.get("hours"):
                meta["hours"] = r["hours"]
            if r.get("description"):
                meta["description"] = r["description"]
            if r.get("thumbnail"):
                meta["thumbnail"] = r["thumbnail"]
            if r.get("data_id"):
                meta["data_id"] = r["data_id"]
            if r.get("price_level"):
                meta["price_level"] = r["price_level"]

            fields = {
                "business_name": r.get("business_name", ""),
                "address": r.get("address"),
                "postcode": postcode,
                "lat": r.get("lat"),
                "lng": r.get("lng"),
                "rating": r.get("rating"),
                "review_count": r.get("review_count") or 0,
                "categories": r.get("categories") or None,
                "source": "crawler",
                "enriched": False,
                "meta_data": meta or None,
                "cached_data": r,
                "cached_at": crawled_at,
            }

            if existing:
                for key, val in fields.items():
                    setattr(existing, key, val)
                existing.updated_at = now
                updated_count += 1
            else:
                slug = await generate_unique_slug(session, r.get("business_name", ""), Business)
                biz = Business(google_place_id=pid, slug=slug, **fields)
                session.add(biz)
                new_count += 1

        await session.commit()

    print(f"New: {new_count}")
    print(f"Updated: {updated_count}")
    if skipped:
        print(f"Skipped (no place_id): {skipped}")
    print("Done.")


def main():
    parser = argparse.ArgumentParser(description="Import crawler JSON into businesses table")
    parser.add_argument("--file", required=True, help="Path to crawler JSON file")
    args = parser.parse_args()

    if not Path(args.file).exists():
        print(f"File not found: {args.file}")
        sys.exit(1)

    asyncio.run(run(args.file))


if __name__ == "__main__":
    main()
