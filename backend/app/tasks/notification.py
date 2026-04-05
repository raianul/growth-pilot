import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.tasks import celery_app
from app.tasks.db import run_async, task_session
from app.models.audit import WeeklyAudit
from app.models.organization import Organization
from app.models.outlet import Outlet
from app.models.user import UserProfile

logger = logging.getLogger(__name__)


async def _mark_audit_complete(audit_id: str) -> None:
    async with task_session() as session:
        result = await session.execute(
            select(WeeklyAudit).where(WeeklyAudit.id == uuid.UUID(audit_id))
        )
        audit = result.scalar_one_or_none()
        if audit:
            audit.status = "completed"
            audit.completed_at = datetime.now(timezone.utc)
            progress = audit.phase_progress or {}
            progress["notification"] = "done"
            audit.phase_progress = progress
            audit.current_phase = "done"
            await session.commit()


async def _send_telegram(user: UserProfile, audit_id: str, business_name: str, total_score: int) -> None:
    from app.core.config import settings
    import httpx

    telegram_chat_id = getattr(user, "telegram_chat_id", None)
    if not telegram_chat_id or not settings.telegram_bot_token:
        logger.info("Telegram notification skipped — no chat_id or token configured")
        return

    text = (
        f"GrowthPilot Weekly Audit Complete\n\n"
        f"Business: {business_name}\n"
        f"Score: {total_score}/100\n\n"
        f"Your new missions are ready. Open the app to review them."
    )
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.post(
                f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage",
                json={"chat_id": telegram_chat_id, "text": text},
            )
        except Exception as exc:
            logger.warning("Telegram send failed: %s", exc)


async def _send_email(user: UserProfile, audit_id: str, business_name: str, total_score: int) -> None:
    from app.core.config import settings
    import httpx

    if not settings.resend_api_key or not user.email:
        logger.info("Email notification skipped — no Resend API key or user email")
        return

    payload = {
        "from": "GrowthPilot <noreply@growthpilot.com>",
        "to": [user.email],
        "subject": f"Your weekly audit is ready — {business_name}",
        "text": (
            f"Hi,\n\n"
            f"Your weekly GrowthPilot audit for {business_name} is complete.\n"
            f"Visibility score: {total_score}/100\n\n"
            f"Log in to view your new missions and content drafts.\n\n"
            f"The GrowthPilot Team"
        ),
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json=payload,
            )
        except Exception as exc:
            logger.warning("Email send failed: %s", exc)


async def _notify(audit_id: str, outlet_id: str, content_results: list[dict]) -> None:
    """Mark audit done and dispatch Telegram + email notifications."""
    await _mark_audit_complete(audit_id)

    async with task_session() as session:
        outlet_result = await session.execute(
            select(Outlet)
            .options(selectinload(Outlet.organization))
            .where(Outlet.id == uuid.UUID(outlet_id))
        )
        outlet = outlet_result.scalar_one_or_none()
        if outlet is None:
            logger.warning("Outlet %s not found; skipping notifications", outlet_id)
            return

        org = outlet.organization
        business_name = org.business_name if org else "Unknown"

        audit_result = await session.execute(
            select(WeeklyAudit).where(WeeklyAudit.id == uuid.UUID(audit_id))
        )
        audit = audit_result.scalar_one_or_none()
        total_score = audit.total_score if audit else 0

        user_result = await session.execute(
            select(UserProfile).where(UserProfile.id == org.user_id)
        )
        user = user_result.scalar_one_or_none()

    if user is None:
        logger.warning("User for outlet %s not found; skipping notifications", outlet_id)
        return

    await _send_telegram(user, audit_id, business_name, total_score or 0)
    await _send_email(user, audit_id, business_name, total_score or 0)


@celery_app.task(name="send_notification", bind=True, max_retries=0)
def send_notification(self, content_results: list[dict], audit_id: str, outlet_id: str) -> dict:
    """
    Phase 4 — Celery chord callback.

    Marks the audit as completed and sends Telegram + email notifications.

    Parameters
    ----------
    content_results: List of dicts returned by generate_content_for_mission tasks
    audit_id:        UUID string of the WeeklyAudit
    outlet_id:       UUID string of the Outlet
    """
    try:
        run_async(_notify(audit_id, outlet_id, content_results))
        logger.info("Audit %s marked complete and notifications sent", audit_id)
        return {"audit_id": audit_id, "status": "completed"}
    except Exception as exc:
        logger.exception("send_notification failed for audit %s: %s", audit_id, exc)
        return {"audit_id": audit_id, "status": "error"}
