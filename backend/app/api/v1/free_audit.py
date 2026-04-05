import asyncio
import json
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import Depends
from sse_starlette.sse import EventSourceResponse

from app.core.database import get_db, async_session
from app.models.audit import WeeklyAudit
from app.models.dimension import AuditDimension
from app.models.soft_lead import SoftLead
from app.models.business import Business

router = APIRouter(prefix="/audit/free", tags=["free-audit"])


# ---------- Schemas ----------

class FreeAuditRequest(BaseModel):
    google_maps_url: str | None = None
    google_place_id: str | None = None
    renew: bool = False


class FreeAuditTriggerResponse(BaseModel):
    audit_id: UUID
    status: str  # "completed" (cached) or "processing" (new)
    business_name: str | None = None
    address: str | None = None


class FreeAuditStatusResponse(BaseModel):
    audit_id: UUID
    status: str
    phase_progress: dict | None = None
    result: dict | None = None
    validation_error: str | None = None


class FreeAuditCategoryError(BaseModel):
    status: str  # "error"
    code: str  # "unsupported_category"
    message: str
    business_name: str
    detected_category: str


class SoftLeadCaptureRequest(BaseModel):
    name: str | None = None
    email: str
    whatsapp_number: str


class SoftLeadCaptureResponse(BaseModel):
    status: str


# ---------- Helpers ----------

PHASE_MESSAGES = {
    "validation": "Validating your business...",
    "scraping": "Fetching your Google Maps data...",
    "competitors": "Comparing with nearby businesses...",
    "website": "Analyzing your website...",
    "reviews": "Analyzing what your customers say...",
    "local_authority": "Checking local mentions and directories...",
    "ai_readiness": "Checking AI visibility readiness...",
    "gaps": "Finding your biggest opportunities...",
}


DELIVERY_PLATFORMS = {
    "foodpanda.com": {"name": "Foodpanda", "icon": "delivery_dining"},
    "pathao.com": {"name": "Pathao Food", "icon": "delivery_dining"},
    "shohoz.com": {"name": "Shohoz Food", "icon": "delivery_dining"},
    "ubereats.com": {"name": "Uber Eats", "icon": "delivery_dining"},
}

REVIEW_PLATFORMS = {
    "tripadvisor.com": {"name": "TripAdvisor", "icon": "travel_explore"},
    "yelp.com": {"name": "Yelp", "icon": "rate_review"},
    "zomato.com": {"name": "Zomato", "icon": "restaurant"},
}


def _classify_sources(local_auth: dict, la_status: str, mentions: int) -> dict:
    """Split sources into delivery platforms, review sites, and other mentions."""
    sources = local_auth.get("sources") or []

    delivery_found = []
    review_sites = []
    other_mentions = []

    for s in sources:
        domain = (s.get("domain") or "").lower().replace("www.", "")
        matched = False

        for platform_domain, platform_info in DELIVERY_PLATFORMS.items():
            if platform_domain in domain:
                delivery_found.append({**s, "platform": platform_info["name"]})
                matched = True
                break

        if not matched:
            for platform_domain, platform_info in REVIEW_PLATFORMS.items():
                if platform_domain in domain:
                    review_sites.append({**s, "platform": platform_info["name"]})
                    matched = True
                    break

        if not matched:
            other_mentions.append(s)

    # Check which delivery platforms are missing
    found_domains = {(s.get("domain") or "").lower().replace("www.", "") for s in sources}
    delivery_missing = []
    for platform_domain, platform_info in DELIVERY_PLATFORMS.items():
        if not any(platform_domain in d for d in found_domains):
            delivery_missing.append(platform_info["name"])

    return {
        "status": la_status,
        "mention_count": mentions,
        "on_best_of_list": local_auth.get("on_best_of_list", False),
        "sources": sources[:5],
        "delivery_platforms": {
            "found": delivery_found[:5],
            "missing": delivery_missing[:3],
        },
        "review_sites": review_sites[:3],
        "other_mentions": other_mentions[:3],
    }


import math


def _get_enriched_field(gm_data: dict, field: str):
    """Try to get field from local_authority (enriched DB data) or top-level gm_data."""
    la = gm_data.get("local_authority") or {}
    return la.get(field) or gm_data.get(field) or None


def _compute_growthpilot_score(gm_data: dict, social_links: dict, local_auth: dict,
                                menu_highlights: list | None, price_details: dict | None) -> dict:
    """Compute GrowthPilot score out of 5."""
    factors = []

    # Google rating (15%)
    rating = gm_data.get("rating") or 0
    rating_score = min(rating, 5.0)
    factors.append({"name": "Google Rating", "score": round(rating_score, 1), "weight": 15, "detail": f"{rating}★" if rating else "No rating"})

    # Review volume (15%) — logarithmic scale
    reviews = gm_data.get("reviews") or 0
    if reviews >= 1000:
        review_score = 5.0
    elif reviews > 0:
        review_score = min(5.0, (math.log10(reviews) / math.log10(1000)) * 5)
    else:
        review_score = 0
    factors.append({"name": "Review Volume", "score": round(review_score, 1), "weight": 15, "detail": f"{reviews:,} reviews"})

    # Facebook (10%)
    has_fb = 5.0 if social_links.get("facebook") else 0
    factors.append({"name": "Facebook", "score": has_fb, "weight": 10, "detail": "Found" if has_fb else "Not found"})

    # Instagram (10%)
    has_ig = 5.0 if social_links.get("instagram") else 0
    factors.append({"name": "Instagram", "score": has_ig, "weight": 10, "detail": "Found" if has_ig else "Not found"})

    # Website (10%)
    has_web = 5.0 if social_links.get("website") else 0
    factors.append({"name": "Website", "score": has_web, "weight": 10, "detail": "Found" if has_web else "Not found"})

    # Foodpanda (10%)
    has_fp = 5.0 if (local_auth.get("foodpanda_url")) else 0
    factors.append({"name": "Foodpanda", "score": has_fp, "weight": 10, "detail": "Listed" if has_fp else "Not listed"})

    # Directory mentions (5%)
    mention_count = local_auth.get("mention_count") or 0
    if mention_count >= 3:
        dir_score = 5.0
    elif mention_count == 2:
        dir_score = 3.0
    elif mention_count == 1:
        dir_score = 2.0
    else:
        dir_score = 0
    factors.append({"name": "Directory Listings", "score": dir_score, "weight": 5, "detail": f"{mention_count} found"})

    # TikTok/YouTube (5%)
    has_tt_yt = 5.0 if social_links.get("tiktok") else 0
    factors.append({"name": "TikTok / YouTube", "score": has_tt_yt, "weight": 5, "detail": "Found" if has_tt_yt else "Not found"})

    # Menu photos (5%)
    has_menu = 5.0 if menu_highlights else 0
    factors.append({"name": "Menu on Google", "score": has_menu, "weight": 5, "detail": f"{len(menu_highlights)} items" if menu_highlights else "No menu"})

    # Price data (5%)
    has_price = 5.0 if price_details else 0
    factors.append({"name": "Price Info", "score": has_price, "weight": 5, "detail": "Available" if has_price else "Not available"})

    # Weighted average
    total_weighted = sum(f["score"] * f["weight"] for f in factors)
    total_weight = sum(f["weight"] for f in factors)
    overall = round(total_weighted / total_weight, 1) if total_weight else 0

    return {
        "score": overall,
        "max": 5.0,
        "factors": factors,
    }


def _build_competitor_scorecard(gm_data: dict, social_links: dict) -> list[dict] | None:
    """Build side-by-side comparison from stored competitor data. No DB queries."""
    competitors_detail = gm_data.get("competitors_detail") or []

    # Only include competitors that have social data (enriched)
    enriched_comps = [c for c in competitors_detail if c.get("website_url") or c.get("facebook_url") or c.get("instagram_url")]
    top_comps = enriched_comps[:3] if enriched_comps else competitors_detail[:3]

    if not top_comps:
        return None

    scorecard = []

    # Owner entry
    scorecard.append({
        "name": gm_data.get("business_name") or gm_data.get("title", "You"),
        "is_owner": True,
        "rating": gm_data.get("rating"),
        "review_count": gm_data.get("reviews") or 0,
        "website": bool(social_links.get("website")),
        "facebook": bool(social_links.get("facebook")),
        "instagram": bool(social_links.get("instagram")),
        "tiktok": bool(social_links.get("tiktok")),
        "foodpanda": bool((gm_data.get("local_authority") or {}).get("foodpanda_url")),
    })

    # Competitor entries
    for c in top_comps:
        scorecard.append({
            "name": c.get("business_name", ""),
            "is_owner": False,
            "rating": c.get("rating"),
            "review_count": c.get("reviews") or c.get("review_count") or 0,
            "website": bool(c.get("website_url")),
            "facebook": bool(c.get("facebook_url")),
            "instagram": bool(c.get("instagram_url")),
            "tiktok": bool(c.get("tiktok_url")),
            "foodpanda": bool(c.get("foodpanda_url")),
        })

    return scorecard


def _build_result(audit: WeeklyAudit, dimensions: list[AuditDimension]) -> dict:
    """Build the full free audit result payload from DB records."""
    gm_dim = next((d for d in dimensions if d.dimension == "google_maps"), None)
    gm_data = (gm_dim.raw_data if gm_dim else None) or {}

    # Business info
    business = {
        "name": gm_data.get("title") or gm_data.get("business_name", ""),
        "address": gm_data.get("address"),
        "rating": gm_data.get("rating"),
        "review_count": gm_data.get("reviews"),
        "place_id": gm_data.get("place_id"),
        "category": gm_data.get("category"),
        "types": gm_data.get("types", []),
        "thumbnail": (gm_data.get("local_authority") or {}).get("thumbnail"),
    }

    # Online presence — status factors in both absolute quality and area context
    rating = gm_data.get("rating") or 0
    reviews = gm_data.get("reviews") or 0
    comp = gm_data.get("competitor_comparison") or {}
    avg_rating = (comp.get("area_average") or {}).get("rating") or 0
    avg_reviews = (comp.get("area_average") or {}).get("review_count") or 0

    # Score: 0-2 points for rating, 0-2 points for reviews
    score = 0
    if rating >= 4.5:
        score += 2
    elif rating >= 4.0:
        score += 1
    if reviews >= 100 or (avg_reviews and reviews >= avg_reviews):
        score += 2
    elif reviews >= 30:
        score += 1

    if score >= 3:
        gm_status = "green"
    elif score >= 2:
        gm_status = "yellow"
    else:
        gm_status = "red"

    # Per-metric comparison signals for frontend coloring
    rating_vs_area = "ahead" if (avg_rating and rating >= avg_rating) else "behind" if avg_rating else "neutral"
    reviews_vs_area = "ahead" if (avg_reviews and reviews >= avg_reviews) else "behind" if avg_reviews else "neutral"

    # Website status
    website = gm_data.get("website") or {}
    website_url = website.get("url")
    has_content = bool(website.get("content") and not website.get("error"))
    has_website = bool(website_url or has_content)
    if has_content and website.get("has_schema"):
        website_status = "green"
    elif has_content:
        website_status = "yellow"
    elif website_url:
        website_status = "yellow"  # URL exists but couldn't scrape
    else:
        website_status = "red"

    # Local authority status
    local_auth = gm_data.get("local_authority") or {}
    mentions = local_auth.get("mention_count") or 0
    la_status = "green" if mentions >= 5 else "yellow" if mentions >= 1 else "red"

    # AI readiness
    ai_readiness = gm_data.get("ai_readiness") or {}
    ai_score = ai_readiness.get("score", 0)
    ai_status = "green" if ai_score >= 60 else "yellow" if ai_score >= 30 else "red"

    online_presence = {
        "google_maps": {
            "status": gm_status,
            "rating": gm_data.get("rating"),
            "review_count": gm_data.get("reviews"),
            "place_id": gm_data.get("place_id"),
            "rating_vs_area": rating_vs_area,
            "reviews_vs_area": reviews_vs_area,
            "phone": gm_data.get("phone"),
            "menu_link": gm_data.get("menu_link"),
        },
        "website": {
            "status": website_status,
            "has_website": has_website,
            "url": website_url,
            "has_content": has_content,
            "has_schema": website.get("has_schema"),
            "has_blog": website.get("has_blog"),
            "title": website.get("title"),
            "content_quality": (website.get("content_quality") or {}).get("quality"),
        },
        "local_authority": _classify_sources(local_auth, la_status, mentions),
        "ai_readiness": {
            "status": ai_status,
            "score": ai_score,
            "has_schema": ai_readiness.get("has_schema", False),
            "review_quality": ai_readiness.get("review_quality"),
            "nap_consistent": ai_readiness.get("nap_consistent", False),
            "local_mentions": ai_readiness.get("local_mentions", 0),
        },
    }

    competitor_comparison = gm_data.get("competitor_comparison", {})
    review_analysis = gm_data.get("review_analysis", {})
    top_gaps = gm_data.get("top_gaps", [])

    # Social links from local_authority_data (enriched from DB)
    social_profiles = local_auth.get("social_profiles") or {}

    # Don't count social pages as a website
    SOCIAL_DOMAINS = ["facebook.com", "instagram.com", "tiktok.com", "fb.com", "fb.me"]
    real_website = website_url
    if real_website and any(d in real_website.lower() for d in SOCIAL_DOMAINS):
        real_website = None

    social_links = {
        "website": real_website,
        "facebook": social_profiles.get("facebook"),
        "facebook_followers": social_profiles.get("facebook_followers"),
        "instagram": social_profiles.get("instagram"),
        "instagram_followers": social_profiles.get("instagram_followers"),
        "tiktok": social_profiles.get("tiktok"),
    }

    # Menu highlights from enriched metadata — filter out junk
    raw_menu = _get_enriched_field(gm_data, "menu_highlights")
    skip_menu = {"price", "prices", "menu", "popular", "most popular", "top picks", "categories", "all"}
    if raw_menu and isinstance(raw_menu, list):
        seen = set()
        menu_highlights = []
        for m in raw_menu:
            title = (m.get("title") or "").strip()
            if not title or title.lower() in skip_menu or title.lower() in seen:
                continue
            seen.add(title.lower())
            menu_highlights.append(m)
        menu_highlights = menu_highlights[:8] or None
    else:
        menu_highlights = None

    # Price details from enriched metadata
    price_details = _get_enriched_field(gm_data, "price_details")

    # Competitor scorecard
    competitor_scorecard = _build_competitor_scorecard(gm_data, social_links)

    # GrowthPilot Score
    growthpilot_score = _compute_growthpilot_score(
        gm_data, social_links, local_auth, menu_highlights, price_details
    )

    return {
        "business": business,
        "growthpilot_score": growthpilot_score,
        "competitor_scorecard": competitor_scorecard,
        "online_presence": online_presence,
        "social_links": social_links,
        "competitor_comparison": competitor_comparison,
        "review_analysis": review_analysis,
        "top_gaps": top_gaps,
        "menu_highlights": menu_highlights,
        "price_details": price_details,
        "audit_meta": {
            "audited_at": audit.created_at.isoformat() if audit.created_at else None,
            "expires_at": audit.expires_at.isoformat() if audit.expires_at else None,
        },
    }


# ---------- Category Validation ----------

FOOD_KEYWORDS = [
    "restaurant", "cafe", "coffee", "food", "bakery", "bar", "tea", "juice",
    "dessert", "pizza", "burger", "grill", "bistro", "diner", "eatery",
    "kitchen", "sushi", "kebab", "biryani", "ramen", "noodle", "steak",
    "seafood", "bbq", "barbeque", "tandoor", "dim sum", "wok", "taco",
    "ice cream", "gelato", "pastry", "confectionery", "chocolat",
    "meal_delivery", "meal_takeaway", "fast_food", "pub", "brewery",
    "cocktail", "lounge", "canteen", "catering",
]


def _check_food_category(resolved: dict) -> dict:
    """Check if the business is food-related based on Google Maps types and name."""
    types = resolved.get("types") or []
    category = resolved.get("category") or ""
    name = resolved.get("business_name") or ""

    # Combine types + category + business name into one searchable blob
    all_types = " ".join(types).lower() + " " + category.lower() + " " + name.lower()

    for keyword in FOOD_KEYWORDS:
        if keyword in all_types:
            return {"allowed": True, "detected": category or types[0] if types else "unknown"}

    # Not food — figure out what it actually is
    detected = types[0] if types else category or "unknown"
    return {"allowed": False, "detected": detected}


# ---------- Endpoints ----------

@router.post("", response_model=FreeAuditTriggerResponse, status_code=status.HTTP_201_CREATED)
async def create_free_audit(
    body: FreeAuditRequest,
    db: AsyncSession = Depends(get_db),
):
    """Start a free audit. No auth required.

    Accepts either:
    - google_maps_url: resolves via SerpApi (1 API call)
    - google_place_id: looks up from businesses table (0 API calls)
    """
    if not body.google_maps_url and not body.google_place_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either google_maps_url or google_place_id.",
        )

    # --- Resolve place_id and business data ---
    if body.google_place_id:
        # Flow B: lookup from businesses table — no SerpApi call
        result = await db.execute(
            select(Business).where(Business.google_place_id == body.google_place_id)
        )
        biz = result.scalar_one_or_none()
        if not biz:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Business not found in our directory.",
            )

        place_id = biz.google_place_id
        meta = biz.meta_data or {}
        resolved = {
            "business_name": biz.business_name,
            "rating": biz.rating,
            "reviews": biz.review_count,
            "place_id": place_id,
            "address": biz.address or "",
            "city": meta.get("city", ""),
            "category": biz.categories or "",
            "types": [biz.categories] if biz.categories else [],
            "lat": biz.lat,
            "lng": biz.lng,
            "website": biz.website_url,
            "phone": meta.get("phone"),
            "hours": meta.get("hours"),
            "photos_count": None,
            "description": meta.get("description"),
        }
    else:
        # Flow A: resolve from Google Maps URL — 1 SerpApi call
        url = body.google_maps_url.strip()
        valid_prefixes = ["maps.app.goo.gl", "google.com/maps", "maps.google.com", "goo.gl/maps"]
        if not any(p in url for p in valid_prefixes):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Please paste a valid Google Maps link (e.g. https://maps.app.goo.gl/...).",
            )

        from app.services.maps_resolver import resolve_maps_link

        try:
            resolved = await resolve_maps_link(url)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Could not resolve Google Maps URL: {e}",
            )

        place_id = resolved.get("place_id")
        if not place_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not find a business at this Google Maps URL.",
            )

    # --- Check for cached non-expired full audit (skip if renew=True) ---
    now = datetime.now(timezone.utc)
    cached_audit = None
    if not body.renew:
        result = await db.execute(
            select(WeeklyAudit)
            .where(
                WeeklyAudit.google_place_id == place_id,
                WeeklyAudit.is_free_audit == True,
                WeeklyAudit.status == "completed",
                WeeklyAudit.expires_at > now,
                WeeklyAudit.phase_progress["completed"].as_string() == "done",
            )
            .order_by(WeeklyAudit.created_at.desc())
            .limit(1)
        )
        cached_audit = result.scalar_one_or_none()
    if cached_audit:
        return FreeAuditTriggerResponse(
            audit_id=cached_audit.id,
            status="completed",
            business_name=resolved.get("business_name"),
            address=resolved.get("address"),
        )

    # --- Create new audit and kick off pipeline ---
    audit = WeeklyAudit(
        outlet_id=None,
        google_place_id=place_id,
        is_free_audit=True,
        week_number=now.isocalendar()[1],
        status="pending",
        current_phase=None,
        phase_progress={},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(audit)

    try:
        from app.tasks.free_audit import run_free_audit_pipeline
        resolved_data = {
            "business_name": resolved.get("business_name", ""),
            "rating": resolved.get("rating"),
            "reviews": resolved.get("reviews"),
            "place_id": place_id,
            "address": resolved.get("address", ""),
            "city": resolved.get("city", ""),
            "category": resolved.get("category", ""),
            "types": resolved.get("types", []),
            "lat": resolved.get("lat"),
            "lng": resolved.get("lng"),
            "website": resolved.get("website"),
            "menu_link": resolved.get("menu_link"),
            "phone": resolved.get("phone"),
            "hours": resolved.get("hours"),
            "photos_count": resolved.get("photos_count"),
            "description": resolved.get("description"),
        }
        run_free_audit_pipeline.apply_async(args=[
            str(audit.id),
            resolved_data,
        ])
    except Exception:
        pass

    return FreeAuditTriggerResponse(
        audit_id=audit.id,
        status="processing",
        business_name=resolved.get("business_name"),
        address=resolved.get("address"),
    )


@router.get("/{audit_id}/stream")
async def free_audit_stream(audit_id: UUID):
    """SSE stream for free audit progress. No auth required."""

    # Verify audit exists and is a free audit
    async with async_session() as session:
        result = await session.execute(
            select(WeeklyAudit).where(
                WeeklyAudit.id == audit_id,
                WeeklyAudit.is_free_audit == True,
            )
        )
        audit = result.scalar_one_or_none()
    if audit is None:
        raise HTTPException(status_code=404, detail="Audit not found")

    async def event_generator():
        while True:
            async with async_session() as session:
                res = await session.execute(
                    select(WeeklyAudit)
                    .options(selectinload(WeeklyAudit.dimensions))
                    .where(WeeklyAudit.id == audit_id)
                )
                current = res.scalar_one_or_none()

            if current is None:
                break

            phase = current.current_phase or "pending"
            message = PHASE_MESSAGES.get(phase, f"Processing {phase}...")

            yield {
                "event": "progress",
                "data": json.dumps({
                    "phase": phase,
                    "message": message,
                    "status": current.status,
                    "phase_progress": current.phase_progress or {},
                }),
            }

            if current.status in ("completed", "failed", "rejected"):
                if current.status == "completed":
                    result_data = _build_result(current, current.dimensions)
                else:
                    result_data = None

                complete_payload: dict = {
                    "phase": "completed",
                    "status": current.status,
                    "audit_id": str(audit_id),
                    "data": result_data,
                }
                if current.status == "rejected":
                    complete_payload["validation_error"] = (current.phase_progress or {}).get("validation_error")

                yield {
                    "event": "complete",
                    "data": json.dumps(complete_payload),
                }
                break

            await asyncio.sleep(2)

    return EventSourceResponse(event_generator())


@router.get("/{audit_id}", response_model=FreeAuditStatusResponse)
async def get_free_audit(
    audit_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get free audit result. Fallback for when SSE drops. No auth required."""
    result = await db.execute(
        select(WeeklyAudit)
        .options(selectinload(WeeklyAudit.dimensions))
        .where(
            WeeklyAudit.id == audit_id,
            WeeklyAudit.is_free_audit == True,
        )
    )
    audit = result.scalar_one_or_none()
    if audit is None:
        raise HTTPException(status_code=404, detail="Audit not found")

    if audit.status == "completed":
        result_data = _build_result(audit, audit.dimensions)
    else:
        result_data = None

    validation_error = None
    if audit.status == "rejected":
        validation_error = (audit.phase_progress or {}).get("validation_error")

    return FreeAuditStatusResponse(
        audit_id=audit.id,
        status=audit.status,
        phase_progress=audit.phase_progress,
        result=result_data,
        validation_error=validation_error,
    )


@router.post("/{audit_id}/capture", response_model=SoftLeadCaptureResponse)
async def capture_soft_lead(
    audit_id: UUID,
    body: SoftLeadCaptureRequest,
    db: AsyncSession = Depends(get_db),
):
    """Capture email + WhatsApp from soft gate. No auth required."""
    # Find the audit
    result = await db.execute(
        select(WeeklyAudit).where(
            WeeklyAudit.id == audit_id,
            WeeklyAudit.is_free_audit == True,
        )
    )
    audit = result.scalar_one_or_none()
    if audit is None:
        raise HTTPException(status_code=404, detail="Audit not found")

    place_id = audit.google_place_id or ""
    area = (audit.phase_progress or {}).get("competitors_area_name")

    # Check for existing lead with same email + place_id
    result = await db.execute(
        select(SoftLead).where(
            SoftLead.email == body.email,
            SoftLead.google_place_id == place_id,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.whatsapp_number = body.whatsapp_number
        existing.audit_id = audit_id
        if body.name:
            existing.name = body.name
        if area:
            existing.area = area
    else:
        lead = SoftLead(
            name=body.name,
            email=body.email,
            whatsapp_number=body.whatsapp_number,
            google_place_id=place_id,
            audit_id=audit_id,
            area=area,
        )
        db.add(lead)

    await db.commit()
    return SoftLeadCaptureResponse(status="captured")
