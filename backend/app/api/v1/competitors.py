from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.competitor import Competitor
from app.models.organization import Organization
from app.models.outlet import Outlet
from app.models.user import UserProfile
from app.schemas.competitor import CompetitorResponse, CompetitorSwap

router = APIRouter(tags=["competitors"])

MAX_MANUAL_COMPETITORS = 1


@router.get("/outlets/{outlet_id}/competitors", response_model=list[CompetitorResponse])
async def list_competitors(
    outlet_id: UUID,
    user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Competitor]:
    # Verify outlet ownership via organization join
    result = await db.execute(
        select(Outlet)
        .join(Organization, Outlet.organization_id == Organization.id)
        .where(Outlet.id == outlet_id, Organization.user_id == user.id)
    )
    outlet = result.scalar_one_or_none()
    if outlet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outlet not found")

    comp_result = await db.execute(
        select(Competitor).where(Competitor.outlet_id == outlet_id)
    )
    return list(comp_result.scalars().all())


@router.put(
    "/outlets/{outlet_id}/competitors/{competitor_id}/swap",
    response_model=CompetitorResponse,
)
async def swap_competitor(
    outlet_id: UUID,
    competitor_id: UUID,
    payload: CompetitorSwap,
    user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Competitor:
    # Verify outlet ownership via organization join
    result = await db.execute(
        select(Outlet)
        .join(Organization, Outlet.organization_id == Organization.id)
        .where(Outlet.id == outlet_id, Organization.user_id == user.id)
    )
    outlet = result.scalar_one_or_none()
    if outlet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outlet not found")

    # Enforce max 1 manual competitor
    manual_result = await db.execute(
        select(Competitor).where(
            Competitor.outlet_id == outlet_id,
            Competitor.source == "manual",
            Competitor.id != competitor_id,
        )
    )
    existing_manual = manual_result.scalars().all()
    if len(existing_manual) >= MAX_MANUAL_COMPETITORS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Maximum of 1 manual competitor allowed. Remove the existing one first.",
        )

    # Fetch the competitor being swapped
    comp_result = await db.execute(
        select(Competitor).where(
            Competitor.id == competitor_id,
            Competitor.outlet_id == outlet_id,
        )
    )
    competitor = comp_result.scalar_one_or_none()
    if competitor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competitor not found")

    competitor.business_name = payload.business_name
    competitor.source = "manual"
    competitor.google_place_id = None
    competitor.latest_score = None
    competitor.gap_analysis = None

    await db.commit()
    await db.refresh(competitor)
    return competitor
