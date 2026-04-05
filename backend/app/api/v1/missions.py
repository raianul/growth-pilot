from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import require_tier
from app.models.audit import WeeklyAudit
from app.models.content import ContentDraft
from app.models.mission import Mission
from app.models.organization import Organization
from app.models.outlet import Outlet
from app.models.user import UserProfile
from app.schemas.mission import ContentDraftResponse, MissionResponse, MissionStatusUpdate

router = APIRouter(tags=["missions"])

VALID_STATUSES = {"active", "completed", "skipped", "pending"}


@router.get("/audits/{audit_id}/missions", response_model=list[MissionResponse])
async def list_missions(
    audit_id: UUID,
    user: UserProfile = Depends(require_tier("pro")),
    db: AsyncSession = Depends(get_db),
) -> list[Mission]:
    # Verify the audit belongs to an outlet the user owns
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

    missions_result = await db.execute(
        select(Mission).where(Mission.audit_id == audit_id).order_by(Mission.sort_order)
    )
    return list(missions_result.scalars().all())


@router.patch("/missions/{mission_id}", response_model=MissionResponse)
async def update_mission_status(
    mission_id: UUID,
    payload: MissionStatusUpdate,
    user: UserProfile = Depends(require_tier("pro")),
    db: AsyncSession = Depends(get_db),
) -> Mission:
    if payload.status not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"status must be one of {sorted(VALID_STATUSES)}",
        )

    # Fetch mission with ownership check via outlet -> organization chain
    result = await db.execute(
        select(Mission)
        .join(Outlet, Mission.outlet_id == Outlet.id)
        .join(Organization, Outlet.organization_id == Organization.id)
        .where(
            Mission.id == mission_id,
            Organization.user_id == user.id,
        )
    )
    mission = result.scalar_one_or_none()
    if mission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")

    mission.status = payload.status
    await db.commit()
    await db.refresh(mission)
    return mission


@router.get("/missions/{mission_id}/content", response_model=list[ContentDraftResponse])
async def get_mission_content(
    mission_id: UUID,
    user: UserProfile = Depends(require_tier("pro")),
    db: AsyncSession = Depends(get_db),
) -> list[ContentDraft]:
    # Verify ownership via outlet -> organization chain
    result = await db.execute(
        select(Mission)
        .join(Outlet, Mission.outlet_id == Outlet.id)
        .join(Organization, Outlet.organization_id == Organization.id)
        .where(
            Mission.id == mission_id,
            Organization.user_id == user.id,
        )
    )
    mission = result.scalar_one_or_none()
    if mission is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mission not found")

    drafts_result = await db.execute(
        select(ContentDraft).where(ContentDraft.mission_id == mission_id)
    )
    return list(drafts_result.scalars().all())


@router.post("/content/{content_id}/copied", status_code=status.HTTP_204_NO_CONTENT)
async def track_copy(
    content_id: UUID,
    user: UserProfile = Depends(require_tier("pro")),
    db: AsyncSession = Depends(get_db),
) -> Response:
    # Fetch draft and verify ownership via mission -> outlet -> organization chain
    result = await db.execute(
        select(ContentDraft)
        .join(Mission, ContentDraft.mission_id == Mission.id)
        .join(Outlet, Mission.outlet_id == Outlet.id)
        .join(Organization, Outlet.organization_id == Organization.id)
        .where(
            ContentDraft.id == content_id,
            Organization.user_id == user.id,
        )
    )
    draft = result.scalar_one_or_none()
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content draft not found")

    draft.copy_count += 1
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
