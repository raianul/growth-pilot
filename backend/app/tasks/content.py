import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.tasks import celery_app
from app.tasks.db import run_async, task_session
from app.models.content import ContentDraft
from app.models.mission import Mission
from app.models.organization import Organization
from app.models.outlet import Outlet

logger = logging.getLogger(__name__)


async def _generate_and_save(
    mission_id: str,
    outlet_id: str,
    mission_title: str,
    channel: str,
) -> dict:
    """Call Claude Haiku to generate content and persist as ContentDraft."""
    from app.services.claude_ai import generate_content

    async with task_session() as session:
        outlet_result = await session.execute(
            select(Outlet)
            .options(selectinload(Outlet.organization))
            .where(Outlet.id == uuid.UUID(outlet_id))
        )
        outlet = outlet_result.scalar_one_or_none()
        org = outlet.organization if outlet else None
        business_name = org.business_name if org else "Unknown"
        brand_voice = (org.tone_of_voice if org else None) or "professional and friendly"

    content = await generate_content(
        mission_title=mission_title,
        channel=channel,
        brand_name=business_name,
        brand_voice=brand_voice,
        context={"mission_id": mission_id},
    )

    async with task_session() as session:
        draft = ContentDraft(
            mission_id=uuid.UUID(mission_id),
            channel=channel,
            title=content.get("title", ""),
            body=content.get("body", ""),
        )
        session.add(draft)
        await session.flush()
        draft_id = str(draft.id)
        await session.commit()

    return {
        "mission_id": mission_id,
        "draft_id": draft_id,
        "channel": channel,
        "title": content.get("title", ""),
    }


@celery_app.task(name="generate_content_for_mission", bind=True, max_retries=0)
def generate_content_for_mission(
    self,
    index: int,
    audit_id: str,
    mission_id: str,
    outlet_id: str,
    mission_title: str,
    channel: str,
) -> dict:
    """
    Phase 3 — call Claude Haiku and save a ContentDraft for one mission.

    Parameters
    ----------
    index:         Position of this mission in the batch (0-based)
    audit_id:      UUID of the parent WeeklyAudit
    mission_id:    UUID of the Mission row to attach the draft to
    outlet_id:     UUID of the Outlet
    mission_title: Title of the mission (passed as context to Haiku)
    channel:       Target channel (google_maps, website, social, reddit, youtube)
    """
    try:
        result = run_async(
            _generate_and_save(mission_id, outlet_id, mission_title, channel)
        )
        return result
    except Exception as exc:
        logger.exception(
            "generate_content_for_mission failed for mission %s: %s", mission_id, exc
        )
        return {
            "mission_id": mission_id,
            "draft_id": None,
            "channel": channel,
            "title": "",
        }
