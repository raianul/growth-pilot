from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.deps import require_tier
from app.models.audit import WeeklyAudit
from app.models.organization import Organization
from app.models.outlet import Outlet
from app.models.mission import Mission
from app.models.user import UserProfile
from app.schemas.audit import AuditResponse, ScoreHistoryItem, DimensionResponse
from app.schemas.dashboard import DashboardResponse
from app.schemas.mission import MissionResponse

router = APIRouter(tags=["dashboard"])


@router.get("/outlets/{outlet_id}/dashboard", response_model=DashboardResponse)
async def get_dashboard(
    outlet_id: UUID,
    user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> DashboardResponse:
    # Verify outlet ownership via organization join, load organization eagerly
    result = await db.execute(
        select(Outlet)
        .join(Organization, Outlet.organization_id == Organization.id)
        .options(selectinload(Outlet.organization))
        .where(Outlet.id == outlet_id, Organization.user_id == user.id)
    )
    outlet = result.scalar_one_or_none()
    if outlet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outlet not found")

    # Fetch latest audit with dimensions eagerly loaded
    audit_result = await db.execute(
        select(WeeklyAudit)
        .options(selectinload(WeeklyAudit.dimensions))
        .where(WeeklyAudit.outlet_id == outlet_id)
        .order_by(WeeklyAudit.created_at.desc())
        .limit(1)
    )
    latest_audit = audit_result.scalar_one_or_none()

    # Fetch active missions for this outlet, sorted by priority descending
    missions_result = await db.execute(
        select(Mission).where(
            Mission.outlet_id == outlet_id,
            Mission.status.in_(["pending", "active"]),
        ).order_by(Mission.priority_score.desc().nullslast(), Mission.sort_order)
    )
    active_missions = list(missions_result.scalars().all())

    latest_audit_response = None
    if latest_audit is not None:
        latest_audit_response = AuditResponse.model_validate(latest_audit)

    return DashboardResponse(
        outlet_id=outlet_id,
        outlet_name=outlet.outlet_name,
        organization_name=outlet.organization.business_name,
        latest_audit=latest_audit_response,
        active_missions=[MissionResponse.model_validate(m) for m in active_missions],
        next_audit_at=outlet.next_audit_at,
    )


@router.get("/outlets/{outlet_id}/scores/history", response_model=list[ScoreHistoryItem])
async def get_score_history(
    outlet_id: UUID,
    user: UserProfile = Depends(require_tier("pro")),
    db: AsyncSession = Depends(get_db),
) -> list[ScoreHistoryItem]:
    # Verify outlet ownership via organization join
    result = await db.execute(
        select(Outlet)
        .join(Organization, Outlet.organization_id == Organization.id)
        .where(Outlet.id == outlet_id, Organization.user_id == user.id)
    )
    outlet = result.scalar_one_or_none()
    if outlet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outlet not found")

    audits_result = await db.execute(
        select(WeeklyAudit)
        .options(selectinload(WeeklyAudit.dimensions))
        .where(
            WeeklyAudit.outlet_id == outlet_id,
            WeeklyAudit.total_score.isnot(None),
        )
        .order_by(WeeklyAudit.week_number)
    )
    audits = list(audits_result.scalars().all())

    history = []
    for audit in audits:
        history.append(
            ScoreHistoryItem(
                week_number=audit.week_number,
                score=audit.total_score,
                dimensions=[DimensionResponse.model_validate(d) for d in audit.dimensions],
            )
        )
    return history
