#!/usr/bin/env python3
"""
Run Google Maps audits for all competitors in a seeded area.

Usage:
    cd backend && python ../scripts/audit_area.py --area "Uttara 11"
"""
import argparse
import asyncio
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from sqlalchemy import select, func
from app.core.database import async_session
from app.models.seeded_area import SeededArea
from app.models.competitor import Competitor
from app.models.audit import WeeklyAudit
from app.models.dimension import AuditDimension


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


async def audit_competitor(session, comp: Competitor) -> dict:
    """Run Google Maps audit for a single competitor. Returns result dict."""
    from app.services.maps_resolver import resolve_maps_link
    from app.services.serpapi import fetch_google_maps_data

    maps_data = None

    # Prefer maps_url for exact resolution
    if comp.maps_url:
        try:
            resolved = await resolve_maps_link(comp.maps_url)
            if resolved and "error" not in resolved and resolved.get("place_id"):
                maps_data = {
                    "place_id": resolved.get("place_id"),
                    "position": 1,
                    "rating": resolved.get("rating"),
                    "reviews": resolved.get("reviews"),
                    "title": resolved.get("business_name", comp.business_name),
                    "address": resolved.get("address"),
                    "city": resolved.get("city"),
                    "category": resolved.get("category"),
                    "types": resolved.get("types", []),
                }
        except Exception:
            pass  # fall through to name search

    # Fallback to name search
    if not maps_data:
        try:
            maps_data = await fetch_google_maps_data(
                comp.business_name, comp.area or "", "restaurant"
            )
        except Exception as e:
            raise RuntimeError(f"All Google Maps lookups failed: {e}")

    now = datetime.now(timezone.utc)

    # Create weekly_audits record
    audit = WeeklyAudit(
        outlet_id=None,
        google_place_id=maps_data.get("place_id"),
        is_free_audit=True,
        week_number=now.isocalendar()[1],
        status="completed",
        current_phase="google_maps",
        total_score=None,
        phase_progress={"google_maps": "done"},
        created_at=now,
        completed_at=now,
        expires_at=now + timedelta(days=30),
    )
    session.add(audit)
    await session.flush()

    # Create audit_dimensions record
    dimension = AuditDimension(
        audit_id=audit.id,
        dimension="google_maps",
        score=0,
        weight=0.30,
        is_stale=False,
        raw_data=maps_data,
    )
    session.add(dimension)

    # Update competitor cached_data
    comp.cached_data = maps_data
    comp.cached_at = now
    if maps_data.get("place_id") and not comp.google_place_id:
        comp.google_place_id = maps_data["place_id"]

    return maps_data


async def run(area_name: str) -> None:
    area_slug = slugify(area_name)

    async with async_session() as session:
        # Find seeded area
        result = await session.execute(
            select(SeededArea).where(SeededArea.name == area_slug)
        )
        seeded_area = result.scalar_one_or_none()
        if not seeded_area:
            print(f"Area '{area_slug}' not found. Seed it first with seed_area.py.")
            sys.exit(1)

        # Find all competitors in this area
        result = await session.execute(
            select(Competitor).where(Competitor.seeded_area_id == seeded_area.id)
        )
        competitors = result.scalars().all()

        if not competitors:
            print(f"No competitors found in area '{area_slug}'.")
            sys.exit(1)

        total = len(competitors)
        print(f"Auditing {total} businesses in {area_slug}...\n")

        failures = []

        for i, comp in enumerate(competitors, 1):
            label = f"[{i}/{total}] {comp.business_name}"
            try:
                maps_data = await audit_competitor(session, comp)
                rating = maps_data.get("rating")
                reviews = maps_data.get("reviews")
                rating_str = f"{rating}\u2605" if rating else "no rating"
                reviews_str = f"{reviews} reviews" if reviews else "no reviews"
                print(f"{label}... done ({rating_str}, {reviews_str})")
            except Exception as e:
                failures.append((comp.business_name, str(e)))
                print(f"{label}... FAILED ({e})")

        # Update area status
        seeded_area.status = "ready"
        await session.commit()

        # Summary
        succeeded = total - len(failures)
        print(f"\nDone: {succeeded}/{total} succeeded.")
        if failures:
            print("\nFailures:")
            for name, err in failures:
                print(f"  - {name}: {err}")


def main():
    parser = argparse.ArgumentParser(description="Audit all competitors in a seeded area")
    parser.add_argument("--area", required=True, help="Area name (e.g. 'Uttara 11')")
    args = parser.parse_args()
    asyncio.run(run(args.area))


if __name__ == "__main__":
    main()
