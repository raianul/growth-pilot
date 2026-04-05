import json
import logging
import uuid

from sqlalchemy import select

from app.tasks import celery_app
from app.tasks.db import run_async, task_session
from app.models.audit import WeeklyAudit
from app.services.cache import scrape_with_fallback
from app.core.config import settings

logger = logging.getLogger(__name__)


def update_audit_phase(audit_id: str, phase: str, status: str) -> None:
    """Update audit phase progress in DB with row locking to avoid race conditions."""

    async def _update():
        async with task_session() as session:
            result = await session.execute(
                select(WeeklyAudit)
                .where(WeeklyAudit.id == uuid.UUID(audit_id))
                .with_for_update()
            )
            audit = result.scalar_one_or_none()
            if audit is None:
                return
            progress = dict(audit.phase_progress or {})
            progress[phase] = status
            audit.phase_progress = progress
            audit.current_phase = phase
            await session.commit()

    run_async(_update())


@celery_app.task(name="scrape_google_maps", bind=True, max_retries=0)
def scrape_google_maps(
    self,
    audit_id: str,
    outlet_id: str,
    business_name: str,
    city: str,
    category: str,
    maps_url: str | None = None,
) -> dict:
    """Fetch Google Maps ranking data for an outlet.

    If maps_url is provided, resolve it for exact match.
    Otherwise fall back to name+city+category search.
    """
    from app.services.serpapi import fetch_google_maps_data

    update_audit_phase(audit_id, "google_maps", "running")
    try:
        async def _scrape():
            # Prefer maps_url for exact resolution
            if maps_url:
                from app.services.maps_resolver import resolve_maps_link
                result = await resolve_maps_link(maps_url)
                if result and "error" not in result and result.get("place_id"):
                    return {
                        "place_id": result.get("place_id"),
                        "position": 1,
                        "rating": result.get("rating"),
                        "reviews": result.get("reviews"),
                        "title": result.get("business_name", business_name),
                    }
            # Fallback to name search
            return await fetch_google_maps_data(business_name, city, category)

        result = run_async(scrape_with_fallback("serpapi", outlet_id, _scrape))
        update_audit_phase(audit_id, "google_maps", "done")
        return {"data": result.data, "is_stale": result.is_stale, "dimension": "google_maps"}
    except Exception as exc:
        update_audit_phase(audit_id, "google_maps", "error")
        logger.exception("scrape_google_maps failed for outlet %s: %s", outlet_id, exc)
        return {"data": None, "is_stale": True, "dimension": "google_maps"}


@celery_app.task(name="scrape_website_task", bind=True, max_retries=0)
def scrape_website_task(
    self,
    audit_id: str,
    outlet_id: str,
    website_url: str,
    business_name: str = "",
) -> dict:
    """Scrape an outlet's website using Firecrawl, then run AI content quality assessment."""
    from app.services.firecrawl import scrape_website

    update_audit_phase(audit_id, "website", "running")
    try:
        async def _scrape():
            return await scrape_website(website_url)

        result = run_async(scrape_with_fallback("firecrawl", outlet_id, _scrape))

        # Run AI content quality assessment if we have content
        if result.data and result.data.get("content") and not result.data.get("error"):
            from app.services.claude_ai import assess_content_quality
            try:
                quality = run_async(assess_content_quality(business_name, result.data["content"]))
                result.data["content_quality"] = quality
            except Exception as qa_exc:
                logger.warning("Content quality assessment failed for outlet %s: %s", outlet_id, qa_exc)
                result.data["content_quality"] = None

        update_audit_phase(audit_id, "website", "done")
        return {"data": result.data, "is_stale": result.is_stale, "dimension": "website"}
    except Exception as exc:
        update_audit_phase(audit_id, "website", "error")
        logger.exception("scrape_website_task failed for outlet %s: %s", outlet_id, exc)
        return {"data": None, "is_stale": True, "dimension": "website"}


@celery_app.task(name="scrape_local_authority_task", bind=True, max_retries=0)
def scrape_local_authority_task(
    self,
    audit_id: str,
    outlet_id: str,
    business_name: str,
    city: str,
) -> dict:
    """Scrape local authority signals (blog mentions, best-of lists, directories) for an outlet."""
    from app.services.local_authority import fetch_local_authority

    update_audit_phase(audit_id, "local_authority", "running")
    try:
        async def _scrape():
            return await fetch_local_authority(business_name, city)

        result = run_async(scrape_with_fallback("local_authority", outlet_id, _scrape))
        update_audit_phase(audit_id, "local_authority", "done")
        return {"data": result.data, "is_stale": result.is_stale, "dimension": "local_authority"}
    except Exception as exc:
        update_audit_phase(audit_id, "local_authority", "error")
        logger.exception("scrape_local_authority_task failed for outlet %s: %s", outlet_id, exc)
        return {"data": None, "is_stale": True, "dimension": "local_authority"}


@celery_app.task(name="scrape_youtube_task", bind=True, max_retries=0)
def scrape_youtube_task(
    self,
    audit_id: str,
    outlet_id: str,
    business_name: str,
    city: str,
) -> dict:
    """Scrape YouTube presence for an outlet."""
    from app.services.youtube import scrape_youtube

    update_audit_phase(audit_id, "youtube", "running")
    try:
        async def _scrape():
            return await scrape_youtube(business_name, city)

        result = run_async(scrape_with_fallback("youtube", outlet_id, _scrape))
        update_audit_phase(audit_id, "youtube", "done")
        return {"data": result.data, "is_stale": result.is_stale, "dimension": "youtube"}
    except Exception as exc:
        update_audit_phase(audit_id, "youtube", "error")
        logger.exception("scrape_youtube_task failed for outlet %s: %s", outlet_id, exc)
        return {"data": None, "is_stale": True, "dimension": "youtube"}


@celery_app.task(name="fetch_reviews_task", bind=True, max_retries=0)
def fetch_reviews_task(self, audit_id: str, outlet_id: str, place_id: str, business_name: str) -> dict:
    """Fetch and analyze Google Maps reviews."""
    from app.services.reviews import fetch_google_reviews
    from app.services.claude_ai import analyze_reviews

    update_audit_phase(audit_id, "reviews", "running")
    try:
        if settings.dev_mode and not settings.serpapi_key:
            update_audit_phase(audit_id, "reviews", "done")
            return {"data": {"reviews": [], "analysis": {"summary": "Mock: no reviews fetched in dev mode"}, "total_fetched": 0}, "is_stale": False, "dimension": "reviews"}

        reviews = run_async(fetch_google_reviews(place_id))

        analysis = {}
        if reviews:
            analysis = run_async(analyze_reviews(business_name, reviews))

        result = {
            "reviews": reviews[:10],  # store top 10
            "analysis": analysis,
            "total_fetched": len(reviews),
        }

        update_audit_phase(audit_id, "reviews", "done")
        return {"data": result, "is_stale": False, "dimension": "reviews"}
    except Exception as exc:
        update_audit_phase(audit_id, "reviews", "error")
        logger.exception("fetch_reviews_task failed: %s", exc)
        return {"data": None, "is_stale": True, "dimension": "reviews"}


@celery_app.task(name="discover_competitors_task", bind=True, max_retries=0)
def discover_competitors_task(
    self,
    audit_id: str,
    outlet_id: str,
    business_name: str,
    city: str,
    category: str,
    exclude_place_id: str | None = None,
) -> dict:
    """Discover competitor businesses in the same category and city."""
    from app.services.serpapi import discover_competitors

    update_audit_phase(audit_id, "competitors", "running")
    try:
        async def _scrape():
            return await discover_competitors(
                business_name, city, category, exclude_place_id=exclude_place_id
            )

        result = run_async(scrape_with_fallback("serpapi", f"{outlet_id}:competitors", _scrape))

        # Save discovered competitors to DB
        if result.data and isinstance(result.data, list):
            async def _save_competitors():
                from app.models.competitor import Competitor
                async with task_session() as session:
                    # Remove old auto-discovered competitors
                    from sqlalchemy import delete
                    await session.execute(
                        delete(Competitor).where(
                            Competitor.outlet_id == uuid.UUID(outlet_id),
                            Competitor.source == "auto",
                        )
                    )
                    for comp in result.data:
                        session.add(Competitor(
                            outlet_id=uuid.UUID(outlet_id),
                            business_name=comp.get("business_name", "Unknown"),
                            google_place_id=comp.get("place_id"),
                            source="auto",
                            latest_score=None,
                            gap_analysis={
                                "rating": comp.get("rating"),
                                "reviews": comp.get("reviews"),
                                "position": comp.get("position"),
                            },
                        ))
                    await session.commit()
            run_async(_save_competitors())

        update_audit_phase(audit_id, "competitors", "done")
        return {"data": result.data, "is_stale": result.is_stale, "dimension": "competitors"}
    except Exception as exc:
        update_audit_phase(audit_id, "competitors", "error")
        logger.exception("discover_competitors_task failed for outlet %s: %s", outlet_id, exc)
        return {"data": None, "is_stale": True, "dimension": "competitors"}
