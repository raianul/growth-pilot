import asyncio
import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.audit import WeeklyAudit
from app.models.organization import Organization
from app.models.outlet import Outlet
from app.models.user import UserProfile
from app.schemas.audit import AuditTriggerResponse

router = APIRouter(tags=["audits"])


@router.post(
    "/outlets/{outlet_id}/audit",
    response_model=AuditTriggerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def trigger_audit(
    outlet_id: UUID,
    user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> AuditTriggerResponse:
    # Verify outlet ownership via organization join
    result = await db.execute(
        select(Outlet)
        .join(Organization, Outlet.organization_id == Organization.id)
        .where(Outlet.id == outlet_id, Organization.user_id == user.id)
    )
    outlet = result.scalar_one_or_none()
    if outlet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outlet not found")

    week_number = datetime.now(timezone.utc).isocalendar()[1]
    audit = WeeklyAudit(
        outlet_id=outlet_id,
        week_number=week_number,
        status="running",
        current_phase=None,
        phase_progress={},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)

    # Enqueue the Celery pipeline (best-effort; don't fail the request if Celery is unavailable)
    try:
        from app.tasks.scheduler import launch_audit_pipeline
        launch_audit_pipeline.apply_async(args=[str(outlet_id), str(audit.id)])
    except Exception:
        pass

    return AuditTriggerResponse(audit_id=audit.id, status=audit.status)


@router.get("/audits/{audit_id}/stream")
async def audit_stream(
    audit_id: UUID,
    user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> EventSourceResponse:
    # Verify the audit belongs to an outlet owned by this user
    result = await db.execute(
        select(WeeklyAudit)
        .join(Outlet, WeeklyAudit.outlet_id == Outlet.id)
        .join(Organization, Outlet.organization_id == Organization.id)
        .where(
            WeeklyAudit.id == audit_id,
            Organization.user_id == user.id,
        )
    )
    audit = result.scalar_one_or_none()
    if audit is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audit not found")

    # Capture the session factory to create a fresh session inside the generator
    from app.core.database import async_session

    async def event_generator():
        while True:
            async with async_session() as session:
                res = await session.execute(
                    select(WeeklyAudit).where(WeeklyAudit.id == audit_id)
                )
                current = res.scalar_one_or_none()

            if current is None:
                break

            yield {
                "event": "progress",
                "data": json.dumps({
                    "status": current.status,
                    "current_phase": current.current_phase,
                    "phase_progress": current.phase_progress or {},
                }),
            }

            if current.status in ("complete", "failed", "completed"):
                yield {
                    "event": "complete",
                    "data": json.dumps({
                        "audit_id": str(audit_id),
                        "status": current.status,
                        "total_score": current.total_score,
                    }),
                }
                break

            await asyncio.sleep(2)

    return EventSourceResponse(event_generator())
