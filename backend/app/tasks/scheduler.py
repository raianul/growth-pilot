import logging
import uuid
from datetime import datetime, timezone

from celery import chord, chain
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.tasks import celery_app
from app.tasks.db import run_async, task_session
from app.models.organization import Organization
from app.models.outlet import Outlet
from app.models.audit import WeeklyAudit

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Beat schedule — run every 5 minutes to find due audits
# ---------------------------------------------------------------------------

celery_app.conf.beat_schedule = {
    "check-due-audits": {
        "task": "check_and_dispatch_audits",
        "schedule": 300.0,  # every 5 minutes
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _load_outlet_for_pipeline(outlet_id: str) -> Outlet | None:
    async with task_session() as session:
        result = await session.execute(
            select(Outlet)
            .options(selectinload(Outlet.organization))
            .where(Outlet.id == uuid.UUID(outlet_id))
        )
        return result.scalar_one_or_none()


async def _create_audit(outlet_id: str) -> str:
    """Create a new WeeklyAudit row and return its UUID string."""
    async with task_session() as session:
        # Derive the week number from ISO calendar
        week_number = datetime.now(timezone.utc).isocalendar()[1]
        audit = WeeklyAudit(
            outlet_id=uuid.UUID(outlet_id),
            week_number=week_number,
            status="running",
            current_phase="scraping",
            phase_progress={"scraping": "pending"},
        )
        session.add(audit)
        await session.flush()
        audit_id = str(audit.id)
        await session.commit()
    return audit_id


async def _get_due_outlets() -> list[tuple[str, str]]:
    """Return (outlet_id, audit_id) tuples for outlets whose next_audit_at <= now."""
    now = datetime.now(timezone.utc)
    async with task_session() as session:
        result = await session.execute(
            select(Outlet).where(Outlet.next_audit_at <= now)
        )
        outlets = result.scalars().all()

    pairs = []
    for outlet in outlets:
        audit_id = await _create_audit(str(outlet.id))
        pairs.append((str(outlet.id), audit_id))
    return pairs


# ---------------------------------------------------------------------------
# Public API: launch a full pipeline for a specific outlet + audit
# ---------------------------------------------------------------------------

@celery_app.task(name="launch_audit_pipeline")
def launch_audit_pipeline(outlet_id: str, audit_id: str) -> str:
    """
    Build and dispatch the full Celery DAG for one outlet audit.

    Phase 1 — chord of parallel scraping tasks
    Phase 2 — chain: compute_visibility_score → analyze_competitor_gaps → generate_missions_task
    Phase 3 — dispatch_content_generation (triggered by generate_missions_task result)

    The DAG is structured as:
        chord(scraping_tasks)(
            chain(compute_visibility_score, analyze_competitor_gaps,
                  generate_missions_task, dispatch_content_generation)
        )
    """
    from app.tasks.scraping import (
        scrape_google_maps,
        scrape_website_task,
        scrape_local_authority_task,
        scrape_youtube_task,
        discover_competitors_task,
        fetch_reviews_task,
    )
    from app.tasks.analysis import (
        compute_visibility_score,
        analyze_competitor_gaps,
        generate_missions_task,
    )

    outlet = run_async(_load_outlet_for_pipeline(outlet_id))
    if outlet is None:
        logger.error("launch_audit_pipeline: outlet %s not found", outlet_id)
        return audit_id

    org = outlet.organization
    business_name = org.business_name if org else "Unknown"
    website_url = org.website_url if org else ""
    category = org.category if org else "general"

    # Phase 1 — parallel scraping
    scraping_tasks = [
        scrape_google_maps.s(audit_id, outlet_id, business_name, outlet.city, category, outlet.maps_url),
        scrape_website_task.s(audit_id, outlet_id, website_url, business_name),
        scrape_local_authority_task.s(audit_id, outlet_id, business_name, outlet.city),
        scrape_youtube_task.s(audit_id, outlet_id, business_name, outlet.city),
        discover_competitors_task.s(
            audit_id, outlet_id, business_name, outlet.city, category,
            outlet.google_place_id,
        ),
        fetch_reviews_task.s(audit_id, outlet_id, outlet.google_place_id or "", business_name),
    ]

    # Phase 2 + 3 — chain after chord callback receives list of scrape results
    # compute_visibility_score receives (scrape_results, audit_id, outlet_id)
    # The chord passes scrape_results as the first positional arg automatically.
    pipeline = chord(scraping_tasks)(
        chain(
            compute_visibility_score.s(audit_id, outlet_id),
            analyze_competitor_gaps.s(),
            generate_missions_task.s(),
            dispatch_content_generation.s(audit_id, outlet_id),
        )
    )

    logger.info("Audit pipeline launched for outlet %s, audit %s", outlet_id, audit_id)
    return audit_id


# ---------------------------------------------------------------------------
# Phase 3: dispatch per-mission content generation + notification callback
# ---------------------------------------------------------------------------

@celery_app.task(name="dispatch_content_generation")
def dispatch_content_generation(missions_result: dict, audit_id: str, outlet_id: str) -> str:
    """
    After missions are generated, fan out content generation tasks (one per mission)
    and wire send_notification as the chord callback.
    """
    from app.tasks.content import generate_content_for_mission
    from app.tasks.notification import send_notification

    missions = missions_result.get("missions", [])
    if not missions:
        logger.warning(
            "dispatch_content_generation: no missions returned for audit %s", audit_id
        )
        # Still mark audit complete via notification task
        send_notification.apply_async(args=([],), kwargs={"audit_id": audit_id, "outlet_id": outlet_id})
        return audit_id

    content_tasks = [
        generate_content_for_mission.s(
            idx,
            audit_id,
            m["mission_id"],
            outlet_id,
            m["title"],
            m["channel"],
        )
        for idx, m in enumerate(missions)
    ]

    chord(content_tasks)(
        send_notification.s(audit_id=audit_id, outlet_id=outlet_id)
    )

    return audit_id


# ---------------------------------------------------------------------------
# Beat task: find outlets whose next_audit_at is due and launch their pipelines
# ---------------------------------------------------------------------------

@celery_app.task(name="check_and_dispatch_audits")
def check_and_dispatch_audits() -> int:
    """
    Celery Beat task — runs every 5 minutes.

    Finds Outlet rows where next_audit_at <= now, creates WeeklyAudit
    rows, and enqueues launch_audit_pipeline for each.
    """
    due_pairs = run_async(_get_due_outlets())
    for outlet_id, audit_id in due_pairs:
        launch_audit_pipeline.apply_async(args=[outlet_id, audit_id])
        logger.info("Dispatched audit pipeline for outlet %s, audit %s", outlet_id, audit_id)

    if due_pairs:
        logger.info("check_and_dispatch_audits: launched %d pipeline(s)", len(due_pairs))
    return len(due_pairs)
