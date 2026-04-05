from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.organization import Organization
from app.models.outlet import Outlet
from app.models.user import UserProfile
from app.schemas.outlet import OutletCreate, OutletResponse, OutletUpdate

router = APIRouter(tags=["outlets"])

OUTLET_LIMITS: dict[str, int | None] = {"free": 1, "pro": 3, "enterprise": None}


@router.get("/outlets", response_model=list[OutletResponse])
async def list_outlets(
    user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Outlet]:
    result = await db.execute(
        select(Outlet)
        .join(Organization, Outlet.organization_id == Organization.id)
        .where(Organization.user_id == user.id)
    )
    return list(result.scalars().all())


@router.post("/outlets", response_model=OutletResponse, status_code=status.HTTP_201_CREATED)
async def create_outlet(
    payload: OutletCreate,
    user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Outlet:
    # Resolve the user's organization
    org_result = await db.execute(
        select(Organization).where(Organization.user_id == user.id)
    )
    org = org_result.scalar_one_or_none()
    if org is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No organization found. Create one first via POST /organizations.",
        )

    # Enforce outlet limit by tier
    limit = OUTLET_LIMITS.get(user.tier)
    if limit is not None:
        existing_result = await db.execute(
            select(Outlet).where(Outlet.organization_id == org.id)
        )
        existing = existing_result.scalars().all()
        if len(existing) >= limit:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "outlet_limit_reached",
                    "limit": limit,
                    "current_tier": user.tier,
                },
            )

    outlet = Outlet(
        organization_id=org.id,
        outlet_name=payload.outlet_name,
        city=payload.city,
        address=payload.address,
        google_place_id=payload.google_place_id,
    )
    db.add(outlet)
    await db.commit()
    await db.refresh(outlet)
    return outlet


@router.patch("/outlets/{outlet_id}", response_model=OutletResponse)
async def update_outlet(
    outlet_id: UUID,
    payload: OutletUpdate,
    user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Outlet:
    result = await db.execute(
        select(Outlet)
        .join(Organization, Outlet.organization_id == Organization.id)
        .where(Outlet.id == outlet_id, Organization.user_id == user.id)
    )
    outlet = result.scalar_one_or_none()
    if outlet is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outlet not found")

    if payload.outlet_name is not None:
        outlet.outlet_name = payload.outlet_name
    if payload.city is not None:
        outlet.city = payload.city
    if payload.address is not None:
        outlet.address = payload.address
    if payload.google_place_id is not None:
        outlet.google_place_id = payload.google_place_id

    await db.commit()
    await db.refresh(outlet)
    return outlet
