from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.organization import Organization
from app.models.user import UserProfile
from app.schemas.organization import OrganizationCreate, OrganizationResponse, OrganizationUpdate

router = APIRouter(tags=["organizations"])


@router.post("/organizations", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    payload: OrganizationCreate,
    user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    # Each user may only have one organization
    result = await db.execute(
        select(Organization).where(Organization.user_id == user.id)
    )
    existing = result.scalar_one_or_none()
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Organization already exists for this user. Use PATCH /organizations/me to update it.",
        )

    org = Organization(
        user_id=user.id,
        business_name=payload.business_name,
        website_url=payload.website_url,
        category=payload.category,
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@router.get("/organizations/me", response_model=OrganizationResponse)
async def get_my_organization(
    user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    result = await db.execute(
        select(Organization).where(Organization.user_id == user.id)
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


@router.patch("/organizations/me", response_model=OrganizationResponse)
async def update_my_organization(
    payload: OrganizationUpdate,
    user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Organization:
    result = await db.execute(
        select(Organization).where(Organization.user_id == user.id)
    )
    org = result.scalar_one_or_none()
    if org is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    if payload.business_name is not None:
        org.business_name = payload.business_name
    if payload.website_url is not None:
        org.website_url = payload.website_url
    if payload.category is not None:
        org.category = payload.category
    if payload.tone_of_voice is not None:
        org.tone_of_voice = payload.tone_of_voice
    if payload.brand_keywords is not None:
        org.brand_keywords = payload.brand_keywords

    await db.commit()
    await db.refresh(org)
    return org
