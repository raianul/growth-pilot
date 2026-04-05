from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.business import Business
from app.models.audit import WeeklyAudit

router = APIRouter(prefix="/businesses", tags=["businesses"])


class BusinessResult(BaseModel):
    id: UUID
    business_name: str
    slug: str | None = None
    google_place_id: str
    rating: float | None = None
    review_count: int
    address: str | None = None
    categories: str | None = None
    postcode: str | None = None
    thumbnail: str | None = None
    model_config = {"from_attributes": True}


class BusinessSearchResponse(BaseModel):
    results: list[BusinessResult]
    total: int


class BusinessDetailResponse(BaseModel):
    business: BusinessResult
    has_audit: bool
    audit_id: str | None = None


@router.get("/search", response_model=BusinessSearchResponse)
async def search_businesses(
    q: str = Query(..., min_length=2),
    postcode: str | None = None,
    categories: str | None = None,
    limit: int = Query(10, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
):
    """Search businesses by name. No auth required."""
    query = select(Business).where(Business.business_name.ilike(f"%{q}%"))

    if postcode:
        query = query.where(Business.postcode == postcode)
    if categories:
        query = query.where(Business.categories == categories)

    query = query.order_by(Business.review_count.desc()).limit(limit)

    result = await db.execute(query)
    businesses = result.scalars().all()

    results = []
    for b in businesses:
        thumb = (b.meta_data or {}).get("thumbnail") or (b.cached_data or {}).get("thumbnail")
        results.append(BusinessResult(
            id=b.id,
            business_name=b.business_name,
            slug=b.slug,
            google_place_id=b.google_place_id,
            rating=b.rating,
            review_count=b.review_count,
            address=b.address,
            categories=b.categories,
            postcode=b.postcode,
            thumbnail=thumb,
        ))

    return BusinessSearchResponse(results=results, total=len(results))


@router.get("/{slug}", response_model=BusinessDetailResponse)
async def get_business_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Lookup a business by slug. Returns business info + cached audit if exists."""
    result = await db.execute(
        select(Business).where(Business.slug == slug)
    )
    biz = result.scalar_one_or_none()
    if not biz:
        raise HTTPException(status_code=404, detail="Business not found")

    thumb = (biz.meta_data or {}).get("thumbnail") or (biz.cached_data or {}).get("thumbnail")

    # Check for cached audit
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    audit_result = await db.execute(
        select(WeeklyAudit)
        .where(
            WeeklyAudit.google_place_id == biz.google_place_id,
            WeeklyAudit.is_free_audit == True,
            WeeklyAudit.status == "completed",
            WeeklyAudit.expires_at > now,
        )
        .order_by(WeeklyAudit.created_at.desc())
        .limit(1)
    )
    cached_audit = audit_result.scalar_one_or_none()

    return BusinessDetailResponse(
        business=BusinessResult(
            id=biz.id,
            business_name=biz.business_name,
            slug=biz.slug,
            google_place_id=biz.google_place_id,
            rating=biz.rating,
            review_count=biz.review_count,
            address=biz.address,
            categories=biz.categories,
            postcode=biz.postcode,
            thumbnail=thumb,
        ),
        has_audit=bool(cached_audit),
        audit_id=str(cached_audit.id) if cached_audit else None,
    )
