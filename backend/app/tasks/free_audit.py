"""
Celery task for the free audit pipeline.

Runs Google Maps scraping, auto-discovers nearby competitors,
review analysis, website/SEO, local authority, AI readiness,
and gap identification.
"""
import logging
import random
import re
import time
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.tasks import celery_app
from app.tasks.db import run_async, task_session
from app.tasks.scraping import update_audit_phase
from app.models.audit import WeeklyAudit
from app.models.dimension import AuditDimension
from app.models.competitor import Competitor

logger = logging.getLogger(__name__)

COMPETITOR_CACHE_DAYS = 30


# ---------- Helpers ----------

def _extract_postcode(address: str) -> str | None:
    """Extract postcode from address. Dhaka postcodes are 4 digits (e.g. 1230)."""
    if not address:
        return None
    match = re.search(r"\b(\d{4,5})\b", address)
    return match.group(1) if match else None


def _extract_city(address: str) -> str:
    """Extract city from address."""
    if not address:
        return ""
    addr_lower = address.lower()
    for city in ["dhaka", "chittagong", "chattogram", "sylhet", "rajshahi", "khulna", "rangpur", "barishal", "mymensingh"]:
        if city in addr_lower:
            return city.capitalize()
    parts = [p.strip() for p in address.split(",")]
    if len(parts) >= 2:
        return parts[-2]
    return ""


# ---------- Competitor Discovery ----------

def _discover_and_cache_competitors(
    lat: str | None, lng: str | None,
    owner_place_id: str,
    owner_address: str,
) -> list[dict]:
    """Auto-discover nearby restaurants, cache by postcode, return comparison list.

    Caching: if competitors with the same postcode exist and cached_at < 30 days, reuse.
    """
    from app.services.serpapi import discover_nearby_restaurants

    postcode = _extract_postcode(owner_address)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=COMPETITOR_CACHE_DAYS)

    # Check postcode-based cache
    if postcode:
        cached = _get_cached_by_postcode(postcode, cutoff, owner_place_id)
        if cached is not None:
            return cached

    # No cache — discover via SerpApi
    if not lat or not lng:
        return _fallback_to_seeded(owner_address, owner_place_id) or []

    nearby = run_async(discover_nearby_restaurants(
        lat, lng, exclude_place_id=owner_place_id, max_results=10
    ))

    if not nearby:
        return _fallback_to_seeded(owner_address, owner_place_id) or []

    # Store in competitors table
    _store_competitors(nearby, postcode, now)

    return [
        {
            "business_name": c["business_name"],
            "rating": c.get("rating"),
            "reviews": c.get("reviews"),
            "place_id": c.get("place_id"),
        }
        for c in nearby
    ]


def _get_cached_by_postcode(postcode: str, cutoff: datetime, exclude_place_id: str) -> list[dict] | None:
    """Return cached competitors for this postcode if fresh, else None."""
    async def _fetch():
        async with task_session() as session:
            result = await session.execute(
                select(Competitor).where(
                    Competitor.postcode == postcode,
                    Competitor.cached_data.isnot(None),
                    Competitor.cached_at > cutoff,
                )
            )
            comps = result.scalars().all()
            if not comps:
                return None

            return [
                {
                    "business_name": c.business_name,
                    "rating": (c.cached_data or {}).get("rating"),
                    "reviews": (c.cached_data or {}).get("reviews"),
                    "place_id": c.google_place_id,
                }
                for c in comps
                if c.google_place_id != exclude_place_id
            ]

    return run_async(_fetch())


def _fallback_to_seeded(address: str, exclude_place_id: str) -> list[dict] | None:
    """Try to find pre-seeded competitors by matching area name in address."""
    from app.models.seeded_area import SeededArea

    async def _find():
        async with task_session() as session:
            result = await session.execute(
                select(SeededArea).where(SeededArea.status.in_(["ready", "active"]))
            )
            areas = result.scalars().all()
            if not areas:
                return None

            combined = (address or "").lower()
            matched = None
            for area in areas:
                tokens = area.name.replace("-", " ").split()
                if all(t in combined for t in tokens):
                    matched = area
                    break
            if not matched:
                return None

            result = await session.execute(
                select(Competitor).where(
                    Competitor.seeded_area_id == matched.id,
                    Competitor.cached_data.isnot(None),
                )
            )
            comps = result.scalars().all()
            return [
                {
                    "business_name": c.business_name,
                    "rating": (c.cached_data or {}).get("rating"),
                    "reviews": (c.cached_data or {}).get("reviews"),
                    "place_id": c.google_place_id,
                }
                for c in comps
                if c.google_place_id != exclude_place_id
            ] or None

    return run_async(_find())


def _store_competitors(nearby: list[dict], postcode: str | None, now: datetime):
    """Upsert auto-discovered competitors. Idempotent by google_place_id."""
    async def _save():
        async with task_session() as session:
            for c in nearby:
                pid = c.get("place_id")
                if not pid:
                    continue

                result = await session.execute(
                    select(Competitor).where(Competitor.google_place_id == pid).limit(1)
                )
                existing = result.scalar_one_or_none()

                cached_data = {
                    "rating": c.get("rating"),
                    "reviews": c.get("reviews"),
                    "address": c.get("address"),
                    "types": c.get("types"),
                    "thumbnail": c.get("thumbnail"),
                }

                if existing:
                    existing.cached_data = cached_data
                    existing.cached_at = now
                    existing.business_name = c["business_name"]
                    if postcode:
                        existing.postcode = postcode
                    if c.get("lat"):
                        existing.lat = float(c["lat"])
                    if c.get("lng"):
                        existing.lng = float(c["lng"])
                else:
                    comp = Competitor(
                        outlet_id=None,
                        seeded_area_id=None,
                        business_name=c["business_name"],
                        google_place_id=pid,
                        area=postcode,
                        postcode=postcode,
                        lat=float(c["lat"]) if c.get("lat") else None,
                        lng=float(c["lng"]) if c.get("lng") else None,
                        source="auto",
                        cached_data=cached_data,
                        cached_at=now,
                    )
                    session.add(comp)

            await session.commit()

    run_async(_save())


# ---------- Comparison & Gaps ----------

def _build_competitor_comparison(business_data: dict, competitors: list[dict]) -> dict:
    if not competitors:
        return {}

    ratings = [c["rating"] for c in competitors if c.get("rating")]
    review_counts = [c["reviews"] for c in competitors if c.get("reviews")]

    avg_rating = round(sum(ratings) / len(ratings), 1) if ratings else None
    avg_reviews = round(sum(review_counts) / len(review_counts)) if review_counts else None

    top_by_reviews = max(competitors, key=lambda c: c.get("reviews") or 0)

    return {
        "area_business_count": len(competitors),
        "you": {
            "rating": business_data.get("rating"),
            "review_count": business_data.get("reviews"),
        },
        "area_average": {
            "rating": avg_rating,
            "review_count": avg_reviews,
        },
        "top_competitor": {
            "name": top_by_reviews.get("business_name"),
            "rating": top_by_reviews.get("rating"),
            "review_count": top_by_reviews.get("reviews"),
        },
    }


def _compute_ai_readiness(maps_data: dict, review_analysis: dict, website_data: dict, local_authority_data: dict) -> dict:
    score = 0

    has_schema = website_data.get("has_schema", False)
    if has_schema:
        score += 30

    review_quality = review_analysis.get("review_quality", "low")
    if review_quality == "high":
        score += 25
    elif review_quality == "medium":
        score += 15
    elif (maps_data.get("reviews") or 0) >= 50:
        score += 10

    gm_title = (maps_data.get("title") or maps_data.get("business_name") or "").lower()
    web_title = (website_data.get("title") or "").lower()
    nap_consistent = bool(gm_title and web_title and (gm_title in web_title or web_title in gm_title))
    if nap_consistent:
        score += 25

    mention_count = local_authority_data.get("mention_count") or 0
    if mention_count >= 3:
        score += 20

    return {
        "score": min(score, 100),
        "has_schema": has_schema,
        "review_quality": review_quality,
        "nap_consistent": nap_consistent,
        "local_mentions": mention_count,
    }


def _identify_gaps(business_data: dict, comparison: dict, review_analysis: dict,
                   website_data: dict = None, local_authority_data: dict = None,
                   maps_data: dict = None) -> list[dict]:
    gaps = []
    maps_data = maps_data or business_data
    website_data = website_data or {}
    local_authority_data = local_authority_data or {}

    your_reviews = business_data.get("reviews") or 0
    your_rating = business_data.get("rating") or 0
    avg_reviews = (comparison.get("area_average") or {}).get("review_count") or 0
    top_reviews = (comparison.get("top_competitor") or {}).get("review_count") or 0
    top_name = (comparison.get("top_competitor") or {}).get("name", "the top competitor")

    if avg_reviews and your_reviews < avg_reviews:
        gap_pct = round((1 - your_reviews / avg_reviews) * 100)
        gaps.append({
            "dimension": "google_maps",
            "type": "review_count",
            "severity": "high" if gap_pct > 50 else "medium",
            "message": f"You have {your_reviews} reviews — {gap_pct}% fewer than the area average ({avg_reviews}). {top_name} has {top_reviews}.",
        })

    avg_rating = (comparison.get("area_average") or {}).get("rating") or 0
    if avg_rating and your_rating < avg_rating:
        gaps.append({
            "dimension": "google_maps",
            "type": "rating",
            "severity": "high" if (avg_rating - your_rating) > 0.3 else "medium",
            "message": f"Your rating is {your_rating}★ — below the area average of {avg_rating}★.",
        })

    website_url = website_data.get("url") or ""
    is_social_as_website = any(
        domain in website_url.lower()
        for domain in ["facebook.com", "instagram.com", "fb.com", "fb.me"]
    )

    if is_social_as_website:
        # Social page used as website URL in Google Maps
        gaps.append({
            "dimension": "website",
            "type": "social_as_website",
            "severity": "high",
            "message": "Your Google Maps listing uses a Facebook/Instagram page as your website. Create a simple one-page website with your menu, hours, and contact info — it helps Google rank you higher and looks more professional to customers.",
        })
        gaps.append({
            "dimension": "google_maps",
            "type": "social_links",
            "severity": "medium",
            "message": "Add your Facebook and Instagram as social links in Google Business Profile instead of using them as your website URL. This way customers can find both your website and social pages.",
        })
    elif not website_data or website_data.get("error") or not website_data.get("content"):
        if not website_url:
            # No website at all
            gaps.append({
                "dimension": "website",
                "type": "missing",
                "severity": "high",
                "message": "No website found. Customers can't find your menu, hours, or contact info outside of Google Maps. Even a simple one-page site makes a big difference.",
            })
        else:
            # Website URL exists but couldn't be scanned
            gaps.append({
                "dimension": "website",
                "type": "scan_failed",
                "severity": "medium",
                "message": f"We found your website ({website_url.replace('https://', '').replace('http://', '').split('/')[0]}) but couldn't scan it. Make sure it's accessible and has your menu, hours, and contact info.",
            })
    else:
        if not website_data.get("has_schema"):
            gaps.append({
                "dimension": "website",
                "type": "schema",
                "severity": "medium",
                "message": "Your website is missing structured data (Schema markup). This helps Google and AI assistants understand your business.",
            })

    # Menu link check
    if not maps_data.get("menu_link"):
        gaps.append({
            "dimension": "google_maps",
            "type": "no_menu",
            "severity": "medium",
            "message": "No menu link found on your Google Maps listing. Adding your menu helps customers decide before visiting and improves your ranking.",
        })

    mention_count = local_authority_data.get("mention_count")
    if mention_count is not None and mention_count < 3:
        gaps.append({
            "dimension": "local_authority",
            "type": "mentions",
            "severity": "medium" if mention_count == 0 else "low",
            "message": f"Only {mention_count} online mentions found. Getting listed on review sites and local blogs boosts your visibility.",
        })

    # Customer complaints as actionable feedback
    complaints = review_analysis.get("top_complaints", [])
    for complaint in complaints[:2]:
        gaps.append({
            "dimension": "google_maps",
            "type": "customer_complaint",
            "severity": "medium",
            "message": f"Customers are saying: {complaint}",
        })

    # Unanswered reviews — separate action item
    suggestions = review_analysis.get("improvement_suggestions", [])
    if suggestions:
        gaps.append({
            "dimension": "google_maps",
            "type": "review_action",
            "severity": "low",
            "message": suggestions[0],
        })

    severity_order = {"high": 0, "medium": 1, "low": 2}
    gaps.sort(key=lambda g: severity_order.get(g["severity"], 3))
    return gaps[:5]


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


def _check_food_category(resolved_data: dict) -> dict:
    """Check if the business is food-related. Returns {allowed, detected}."""
    types = resolved_data.get("types") or []
    category = resolved_data.get("category") or ""
    name = resolved_data.get("business_name") or ""

    all_types = " ".join(types).lower() + " " + category.lower() + " " + name.lower()

    for keyword in FOOD_KEYWORDS:
        if keyword in all_types:
            return {"allowed": True, "detected": category or types[0] if types else "unknown"}

    detected = types[0] if types else category or "unknown"
    return {"allowed": False, "detected": detected}


# ---------- Pipeline ----------

@celery_app.task(name="run_free_audit_pipeline", bind=True, max_retries=0)
def run_free_audit_pipeline(
    self,
    audit_id: str,
    resolved_data: dict,
) -> dict:
    try:
        _run_pipeline(audit_id, resolved_data)
    except Exception as exc:
        logger.exception("Free audit pipeline failed for %s: %s", audit_id, exc)
        _mark_failed(audit_id)
        return {"audit_id": audit_id, "status": "failed", "error": str(exc)}

    return {"audit_id": audit_id, "status": "completed"}


def _mark_failed(audit_id: str):
    async def _update():
        async with task_session() as session:
            result = await session.execute(
                select(WeeklyAudit).where(WeeklyAudit.id == uuid.UUID(audit_id))
            )
            audit = result.scalar_one_or_none()
            if audit:
                audit.status = "failed"
                audit.current_phase = "failed"
                await session.commit()
    run_async(_update())


def _mark_rejected(audit_id: str, detected_category: str):
    """Mark audit as rejected due to unsupported category."""
    async def _update():
        async with task_session() as session:
            audit_uuid = uuid.UUID(audit_id)
            result = await session.execute(
                select(WeeklyAudit).where(WeeklyAudit.id == audit_uuid)
            )
            audit = result.scalar_one_or_none()
            if audit:
                audit.status = "rejected"
                audit.current_phase = "validation"
                progress = dict(audit.phase_progress or {})
                progress["validation"] = "rejected"
                progress["validation_error"] = (
                    f"Google Maps lists this as \"{detected_category}\". "
                    "GrowthPilot currently works for restaurants and cafés only. "
                    "If you own this business, update your category to 'Restaurant' in Google Business Profile."
                )
                audit.phase_progress = progress
                await session.commit()
    run_async(_update())


def _get_competitors_from_db(postcode: str, owner_place_id: str) -> list[dict]:
    """Query businesses table for competitors in the same postcode. Zero API calls."""
    from app.models.business import Business

    async def _fetch():
        async with task_session() as session:
            result = await session.execute(
                select(Business)
                .where(
                    Business.postcode == postcode,
                    Business.google_place_id != owner_place_id,
                )
                .order_by(Business.review_count.desc())
                .limit(10)
            )
            businesses = result.scalars().all()
            return [
                {
                    "business_name": b.business_name,
                    "rating": b.rating,
                    "reviews": b.review_count,
                    "place_id": b.google_place_id,
                    "categories": b.categories,
                    "address": b.address,
                    "website_url": b.website_url,
                    "facebook_url": b.facebook_url,
                    "instagram_url": b.instagram_url,
                    "tiktok_url": b.tiktok_url,
                    "foodpanda_url": (b.meta_data or {}).get("foodpanda_url"),
                    "thumbnail": (b.meta_data or {}).get("thumbnail"),
                }
                for b in businesses
            ]

    return run_async(_fetch())


def _get_local_presence_from_db(place_id: str) -> dict:
    """Read enriched local presence data from businesses table. Zero API calls."""
    from app.models.business import Business

    async def _fetch():
        async with task_session() as session:
            result = await session.execute(
                select(Business).where(Business.google_place_id == place_id)
            )
            biz = result.scalar_one_or_none()
            if not biz:
                return {}

            meta = biz.meta_data or {}
            sources = []

            # Delivery platforms
            if meta.get("foodpanda_url"):
                sources.append({
                    "title": f"{biz.business_name} on Foodpanda",
                    "url": meta["foodpanda_url"],
                    "domain": "www.foodpanda.com.bd",
                    "rating": meta.get("foodpanda_rating"),
                    "reviews": meta.get("foodpanda_reviews"),
                })
            if meta.get("pathao_url"):
                sources.append({
                    "title": f"{biz.business_name} on Pathao",
                    "url": meta["pathao_url"],
                    "domain": "pathao.com",
                })

            # Directory listings
            for listing in (meta.get("directory_listings") or []):
                sources.append({
                    "title": listing.get("title", ""),
                    "url": listing.get("url", ""),
                    "domain": listing.get("source", ""),
                    "rating": listing.get("rating"),
                    "reviews": listing.get("reviews"),
                })

            # YouTube mentions
            for yt in (meta.get("youtube_mentions") or []):
                sources.append({
                    "title": yt.get("title", ""),
                    "url": yt.get("url", ""),
                    "domain": "www.youtube.com",
                })

            # Social profiles with follower counts
            social = {}
            if biz.facebook_url:
                social["facebook"] = biz.facebook_url
                social["facebook_followers"] = meta.get("facebook_followers")
            if biz.instagram_url:
                social["instagram"] = biz.instagram_url
                social["instagram_followers"] = meta.get("instagram_followers")
            if biz.tiktok_url:
                social["tiktok"] = biz.tiktok_url

            return {
                "mention_count": len(sources),
                "sources": sources,
                "on_best_of_list": False,
                "social_profiles": social,
                "website_url": biz.website_url,
                "foodpanda_url": meta.get("foodpanda_url"),
                "pathao_url": meta.get("pathao_url"),
                "directory_listings": meta.get("directory_listings") or [],
                "youtube_mentions": meta.get("youtube_mentions") or [],
                "menu_highlights": meta.get("menu_highlights"),
                "price_details": meta.get("price_details"),
                "merchant_description": meta.get("merchant_description"),
                "phone": meta.get("phone"),
                "thumbnail": meta.get("thumbnail"),
            }

    return run_async(_fetch())


def _run_pipeline(audit_id: str, resolved_data: dict):
    from app.services.reviews import fetch_google_reviews_by_place_id
    from app.services.claude_ai import analyze_reviews
    from app.services.firecrawl import scrape_website
    from app.services.claude_ai import assess_content_quality

    maps_data = resolved_data
    place_id = maps_data["place_id"]
    name = maps_data.get("business_name", "")
    address = maps_data.get("address", "")
    lat = maps_data.get("lat")
    lng = maps_data.get("lng")

    # ---------- Phase 1: Validation ----------
    update_audit_phase(audit_id, "validation", "running")
    time.sleep(random.uniform(2, 3))

    category_check = _check_food_category(maps_data)
    if not category_check["allowed"]:
        _mark_rejected(audit_id, category_check["detected"])
        return

    update_audit_phase(audit_id, "validation", "done")

    # ---------- Phase 2: Google Maps (data already fetched — just mark it) ----------
    update_audit_phase(audit_id, "scraping", "running")
    time.sleep(random.uniform(2, 4))
    update_audit_phase(audit_id, "scraping", "done")

    # ---------- Phase 3: Competitors (from DB — zero API calls) ----------
    update_audit_phase(audit_id, "competitors", "running")
    time.sleep(random.uniform(3, 5))

    postcode = _extract_postcode(address)
    competitors = []

    if postcode:
        competitors = _get_competitors_from_db(postcode, place_id)

    # Fallback to SerpAPI nearby search only if DB has no competitors for this postcode
    if not competitors and lat and lng:
        competitors = _discover_and_cache_competitors(lat, lng, place_id, address)

    comparison = _build_competitor_comparison(maps_data, competitors)

    _update_phase_meta(
        audit_id, "competitors", "done",
        area_name=postcode or "nearby",
        count=len(competitors),
    )

    # ---------- Phase 4: Website/SEO ----------
    update_audit_phase(audit_id, "website", "running")

    website_data = {}
    website_url = maps_data.get("website")

    # If website URL is missing, try enriched data from businesses table
    if not website_url and place_id:
        from app.models.business import Business
        async def _get_website():
            async with task_session() as session:
                result = await session.execute(
                    select(Business.website_url).where(Business.google_place_id == place_id)
                )
                row = result.first()
                return row[0] if row else None
        website_url = run_async(_get_website())

    # Last resort: SerpAPI place details lookup
    if not website_url and place_id:
        try:
            from app.services.serpapi import fetch_place_details
            place_details = run_async(fetch_place_details(place_id))
            if place_details:
                website_url = place_details.get("website")
                if not maps_data.get("menu_link") and place_details.get("menu_link"):
                    maps_data["menu_link"] = place_details["menu_link"]
        except Exception as e:
            logger.warning("Place details lookup failed for %s: %s", place_id, e)

    if website_url:
        try:
            website_data = run_async(scrape_website(website_url))
            if website_data and website_data.get("content") and not website_data.get("error"):
                try:
                    quality = run_async(assess_content_quality(name, website_data["content"]))
                    website_data["content_quality"] = quality
                except Exception as e:
                    logger.warning("Content quality assessment failed: %s", e)
        except Exception as e:
            logger.warning("Website scrape failed for %s: %s", website_url, e)

    update_audit_phase(audit_id, "website", "done")

    # ---------- Phase 5: Local Presence (from enriched DB — zero API calls) ----------
    update_audit_phase(audit_id, "local_authority", "running")
    time.sleep(random.uniform(2, 4))

    local_authority_data = _get_local_presence_from_db(place_id)

    update_audit_phase(audit_id, "local_authority", "done")

    # ---------- Phase 6: AI Readiness (computed) ----------
    update_audit_phase(audit_id, "ai_readiness", "running")
    time.sleep(random.uniform(2, 3))

    ai_readiness = _compute_ai_readiness(maps_data, {}, website_data, local_authority_data)

    update_audit_phase(audit_id, "ai_readiness", "done")

    # ---------- Phase 7: Review Analysis (SerpAPI reviews + LLM) ----------
    update_audit_phase(audit_id, "reviews", "running")

    review_analysis = {}
    try:
        reviews = run_async(fetch_google_reviews_by_place_id(place_id))
        clean_reviews = [r for r in reviews if not r.get("_error")]
        if clean_reviews:
            review_analysis = run_async(analyze_reviews(name, clean_reviews))
    except Exception as e:
        logger.warning("Review analysis failed for %s: %s", audit_id, e)

    # Re-compute AI readiness with review data
    ai_readiness = _compute_ai_readiness(maps_data, review_analysis, website_data, local_authority_data)

    update_audit_phase(audit_id, "reviews", "done")

    # ---------- Phase 8: Gaps ----------
    update_audit_phase(audit_id, "gaps", "running")
    time.sleep(random.uniform(2, 4))

    top_gaps = _identify_gaps(maps_data, comparison, review_analysis, website_data, local_authority_data, maps_data=maps_data)

    update_audit_phase(audit_id, "gaps", "done")

    # ---------- Save ----------
    if website_url:
        website_data["url"] = website_url
    full_raw_data = {
        **maps_data,
        "competitor_comparison": comparison,
        "competitors_detail": competitors,  # Full list with social URLs for scorecard
        "review_analysis": review_analysis,
        "website": website_data,
        "local_authority": local_authority_data,
        "ai_readiness": ai_readiness,
        "top_gaps": top_gaps,
    }
    if postcode:
        full_raw_data["matched_area"] = postcode

    _save_and_complete(audit_id, place_id, full_raw_data)

    # Save/update business in directory
    _upsert_business(maps_data, website_url, postcode)


def _upsert_business(maps_data: dict, website_url: str | None, postcode: str | None):
    """Save or update the business in the businesses table."""
    from app.models.business import Business

    place_id = maps_data.get("place_id")
    if not place_id:
        return

    now = datetime.now(timezone.utc)
    types = maps_data.get("types") or []
    categories = types[0] if types else maps_data.get("category", "")

    # Metadata — display-only fields
    meta = {}
    if maps_data.get("phone"):
        meta["phone"] = maps_data["phone"]
    if maps_data.get("hours"):
        meta["hours"] = maps_data["hours"]
    if maps_data.get("description"):
        meta["description"] = maps_data["description"]
    if maps_data.get("city"):
        meta["city"] = maps_data["city"]

    async def _save():
        async with task_session() as session:
            result = await session.execute(
                select(Business).where(Business.google_place_id == place_id)
            )
            existing = result.scalar_one_or_none()

            fields = {
                "business_name": maps_data.get("business_name") or maps_data.get("title", ""),
                "address": maps_data.get("address"),
                "postcode": postcode,
                "lat": float(maps_data["lat"]) if maps_data.get("lat") else None,
                "lng": float(maps_data["lng"]) if maps_data.get("lng") else None,
                "rating": maps_data.get("rating"),
                "review_count": maps_data.get("reviews") or 0,
                "categories": categories or None,
                "website_url": website_url,
                "meta_data": meta or None,
                "cached_at": now,
            }

            if existing:
                for k, v in fields.items():
                    if v is not None:
                        setattr(existing, k, v)
                existing.updated_at = now
            else:
                from app.utils.slug import generate_unique_slug
                slug = await generate_unique_slug(session, fields["business_name"], Business)
                biz = Business(
                    google_place_id=place_id,
                    slug=slug,
                    source="audit",
                    **fields,
                )
                session.add(biz)

            await session.commit()

    try:
        run_async(_save())
    except Exception as e:
        logger.warning("Failed to upsert business %s: %s", place_id, e)


def _update_phase_meta(audit_id: str, phase: str, status: str, **meta):
    async def _update():
        async with task_session() as session:
            result = await session.execute(
                select(WeeklyAudit)
                .where(WeeklyAudit.id == uuid.UUID(audit_id))
                .with_for_update()
            )
            audit = result.scalar_one_or_none()
            if audit is None:
                return
            progress = dict(audit.phase_progress or {})
            progress[phase] = status
            for k, v in meta.items():
                progress[f"{phase}_{k}"] = v
            audit.phase_progress = progress
            audit.current_phase = phase
            await session.commit()
    run_async(_update())


def _save_and_complete(audit_id: str, place_id: str, raw_data: dict):
    now = datetime.now(timezone.utc)

    async def _save():
        async with task_session() as session:
            audit_uuid = uuid.UUID(audit_id)

            dim = AuditDimension(
                audit_id=audit_uuid,
                dimension="google_maps",
                score=0,
                weight=1.0,
                is_stale=False,
                raw_data=raw_data,
            )
            session.add(dim)

            result = await session.execute(
                select(WeeklyAudit).where(WeeklyAudit.id == audit_uuid)
            )
            audit = result.scalar_one_or_none()
            if audit:
                audit.status = "completed"
                audit.current_phase = "completed"
                audit.completed_at = now
                audit.expires_at = now + timedelta(days=30)
                audit.google_place_id = place_id
                progress = dict(audit.phase_progress or {})
                progress["completed"] = "done"
                audit.phase_progress = progress

            await session.commit()

    run_async(_save())
