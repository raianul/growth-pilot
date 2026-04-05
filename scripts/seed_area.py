#!/usr/bin/env python3
"""
Seed competitor data from a CSV file into a seeded area.

Usage:
    python scripts/seed_area.py --csv data/uttara/sector-11.csv --area "Uttara 11" --city "Dhaka"
"""
import argparse
import asyncio
import csv
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

# Add backend to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select
from app.core.database import async_session
from app.models.seeded_area import SeededArea
from app.models.competitor import Competitor


def slugify(name: str) -> str:
    """Convert area name to slug: 'Uttara 11' -> 'uttara-11'."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def clean(value: str | None) -> str | None:
    """Return None for empty or N/A values."""
    if not value or value.strip().upper() in ("N/A", ""):
        return None
    return value.strip()


def extract_place_id(maps_url: str) -> str | None:
    """Extract place ID from a Google Maps URL if it contains one."""
    if not maps_url:
        return None
    # Handles URLs like https://maps.app.goo.gl/... (short links don't contain place_id)
    # and https://www.google.com/maps/place/...?...!1s<place_id>
    match = re.search(r"!1s(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)", maps_url)
    if match:
        return match.group(1)
    # ChIJ-style place IDs
    match = re.search(r"place_id[=:]([A-Za-z0-9_-]+)", maps_url)
    if match:
        return match.group(1)
    return None


async def seed(csv_path: str, area_name: str, city: str) -> None:
    area_slug = slugify(area_name)

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [row for row in reader if clean(row.get("Name"))]

    if not rows:
        print("No valid rows found in CSV.")
        return

    async with async_session() as session:
        # Upsert seeded area
        result = await session.execute(
            select(SeededArea).where(SeededArea.name == area_slug)
        )
        seeded_area = result.scalar_one_or_none()
        if not seeded_area:
            seeded_area = SeededArea(name=area_slug, city=city)
            session.add(seeded_area)
            await session.flush()

        # Load existing competitors in this area by maps_url for idempotency
        result = await session.execute(
            select(Competitor).where(Competitor.seeded_area_id == seeded_area.id)
        )
        existing = {c.maps_url: c for c in result.scalars().all() if c.maps_url}

        new_count = 0
        updated_count = 0

        for row in rows:
            name = clean(row.get("Name"))
            if not name:
                continue

            maps_url = clean(row.get("Gmap"))
            website_url = clean(row.get("Website"))
            facebook_page_url = clean(row.get("FB"))
            instagram_handle = clean(row.get("Insta"))
            google_place_id = extract_place_id(maps_url) if maps_url else None

            if maps_url and maps_url in existing:
                # Update existing
                comp = existing[maps_url]
                comp.business_name = name
                comp.website_url = website_url
                comp.facebook_page_url = facebook_page_url
                comp.instagram_handle = instagram_handle
                comp.google_place_id = google_place_id
                updated_count += 1
            else:
                # Create new
                comp = Competitor(
                    outlet_id=None,
                    seeded_area_id=seeded_area.id,
                    business_name=name,
                    google_place_id=google_place_id,
                    maps_url=maps_url,
                    website_url=website_url,
                    facebook_page_url=facebook_page_url,
                    instagram_handle=instagram_handle,
                    area=area_slug,
                    source="manual",
                )
                session.add(comp)
                new_count += 1

        total = new_count + updated_count
        seeded_area.business_count = total
        await session.commit()

    print(f"Imported {total} businesses ({new_count} new, {updated_count} updated)")


def main():
    parser = argparse.ArgumentParser(description="Seed competitor data from CSV")
    parser.add_argument("--csv", required=True, help="Path to CSV file")
    parser.add_argument("--area", required=True, help="Area name (e.g. 'Uttara 11')")
    parser.add_argument("--city", required=True, help="City name (e.g. 'Dhaka')")
    args = parser.parse_args()

    if not Path(args.csv).exists():
        print(f"CSV file not found: {args.csv}")
        sys.exit(1)

    asyncio.run(seed(args.csv, args.area, args.city))


if __name__ == "__main__":
    main()
