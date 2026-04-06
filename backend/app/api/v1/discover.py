import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.business import Business
from app.models.discover_user import DiscoverUser
from app.models.user_review import UserReview
from app.services.discover import discover_restaurants, AREA_POSTCODES, POSTCODE_TO_AREA

router = APIRouter(prefix="/discover", tags=["discover"])


# ── Response models ──────────────────────────────────────────────────────────


class ReviewStats(BaseModel):
    total: int
    food_good_pct: Optional[float] = None
    environment_good_pct: Optional[float] = None
    recommend_pct: Optional[float] = None


class RestaurantDetail(BaseModel):
    id: str
    name: str
    slug: Optional[str] = None
    rating: Optional[float] = None
    review_count: int
    address: Optional[str] = None
    postcode: Optional[str] = None
    area: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    categories: Optional[str] = None
    thumbnail: Optional[str] = None
    facebook_url: Optional[str] = None
    instagram_url: Optional[str] = None
    tiktok_url: Optional[str] = None
    website_url: Optional[str] = None
    menu_highlights: list[str] = []
    price_range: Optional[str] = None
    review_stats: ReviewStats


class SearchResponse(BaseModel):
    intent: dict
    results: list[dict]
    nearby: list[dict]
    area: Optional[str] = None


class AreaInfo(BaseModel):
    key: str
    name: str
    postcodes: list[str]


class AreasResponse(BaseModel):
    areas: list[AreaInfo]


class PhoneAuthRequest(BaseModel):
    phone: str
    name: Optional[str] = None


class PhoneAuthResponse(BaseModel):
    user_id: str
    phone: str
    name: Optional[str] = None
    created: bool


class ReviewRequest(BaseModel):
    user_id: str
    business_id: str
    food_good: bool
    environment_good: bool
    would_recommend: bool


class ReviewResponse(BaseModel):
    review_id: str
    business_id: str
    food_good: bool
    environment_good: bool
    would_recommend: bool


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/search", response_model=SearchResponse)
async def search_restaurants(
    q: str = Query(..., min_length=1, description="Natural language query"),
    postcode: Optional[str] = Query(None, description="User's postcode for location context"),
    limit: int = Query(3, ge=1, le=10),
    nearby_limit: int = Query(3, ge=0, le=10),
    db: AsyncSession = Depends(get_db),
):
    """Discover restaurants using a natural language query."""
    result = await discover_restaurants(
        db=db,
        query=q,
        user_postcode=postcode,
        limit=limit,
        nearby_limit=nearby_limit,
    )
    return result


@router.get("/areas", response_model=AreasResponse)
async def list_areas():
    """List all available areas with their postcodes."""
    areas = [
        AreaInfo(
            key=key,
            name=key.capitalize(),
            postcodes=postcodes,
        )
        for key, postcodes in AREA_POSTCODES.items()
    ]
    return AreasResponse(areas=areas)


@router.get("/restaurant/{slug}", response_model=RestaurantDetail)
async def get_restaurant_detail(
    slug: str,
    db: AsyncSession = Depends(get_db),
):
    """Full restaurant detail with KothayKhabo review stats."""
    result = await db.execute(select(Business).where(Business.slug == slug))
    biz = result.scalar_one_or_none()
    if not biz:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    # Aggregate review stats from UserReview table
    stats_result = await db.execute(
        select(
            func.count(UserReview.id).label("total"),
            func.sum(case((UserReview.food_good == True, 1), else_=0)).label("food_good_count"),
            func.sum(case((UserReview.environment_good == True, 1), else_=0)).label("env_good_count"),
            func.sum(case((UserReview.would_recommend == True, 1), else_=0)).label("recommend_count"),
        ).where(UserReview.business_id == biz.id)
    )
    row = stats_result.one()
    total = row.total or 0

    def pct(count) -> Optional[float]:
        if not total:
            return None
        return round((count or 0) / total * 100, 1)

    review_stats = ReviewStats(
        total=total,
        food_good_pct=pct(row.food_good_count),
        environment_good_pct=pct(row.env_good_count),
        recommend_pct=pct(row.recommend_count),
    )

    meta = biz.meta_data or {}
    cached = biz.cached_data or {}
    price = meta.get("price_details") or {}
    price_range = (
        price.get("distribution", [{}])[0].get("price")
        if price.get("distribution")
        else None
    )

    return RestaurantDetail(
        id=str(biz.id),
        name=biz.business_name,
        slug=biz.slug,
        rating=biz.rating,
        review_count=biz.review_count,
        address=biz.address,
        postcode=biz.postcode,
        area=POSTCODE_TO_AREA.get(biz.postcode or "", biz.postcode),
        lat=biz.lat,
        lng=biz.lng,
        categories=biz.categories,
        thumbnail=meta.get("thumbnail") or cached.get("thumbnail"),
        facebook_url=biz.facebook_url,
        instagram_url=biz.instagram_url,
        tiktok_url=biz.tiktok_url,
        website_url=biz.website_url,
        menu_highlights=(meta.get("menu_highlights") or [])[:4],
        price_range=price_range,
        review_stats=review_stats,
    )


@router.post("/auth/phone", response_model=PhoneAuthResponse)
async def phone_auth(
    body: PhoneAuthRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create or find a DiscoverUser by phone number."""
    result = await db.execute(
        select(DiscoverUser).where(DiscoverUser.phone == body.phone)
    )
    user = result.scalar_one_or_none()

    created = False
    if user is None:
        user = DiscoverUser(phone=body.phone, name=body.name)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        created = True

    return PhoneAuthResponse(
        user_id=str(user.id),
        phone=user.phone,
        name=user.name,
        created=created,
    )


@router.post("/review", response_model=ReviewResponse, status_code=201)
async def submit_review(
    body: ReviewRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit a 3-question review. Returns 409 if the user already reviewed this restaurant."""
    try:
        user_id = uuid.UUID(body.user_id)
        business_id = uuid.UUID(body.business_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid user_id or business_id UUID format")

    # Check for duplicate review
    existing = await db.execute(
        select(UserReview).where(
            UserReview.user_id == user_id,
            UserReview.business_id == business_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="You have already reviewed this restaurant")

    review = UserReview(
        user_id=user_id,
        business_id=business_id,
        food_good=body.food_good,
        environment_good=body.environment_good,
        would_recommend=body.would_recommend,
    )
    db.add(review)
    await db.commit()
    await db.refresh(review)

    return ReviewResponse(
        review_id=str(review.id),
        business_id=str(review.business_id),
        food_good=review.food_good,
        environment_good=review.environment_good,
        would_recommend=review.would_recommend,
    )
