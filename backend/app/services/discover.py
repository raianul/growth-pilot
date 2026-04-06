import json
import logging

from sqlalchemy import select, func, or_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.business import Business
from app.models.user_review import UserReview
from app.services.claude_ai import _call_llm

logger = logging.getLogger(__name__)

INTENT_SYSTEM_PROMPT = """You parse natural language restaurant queries into structured JSON.

Given a user query about finding a restaurant, extract:
{
  "cuisine": string or null (e.g. "burger", "biryani", "chinese", "thai"),
  "budget_max_bdt": integer or null (max budget in BDT per person),
  "party_size": integer or null,
  "vibe": string or null (e.g. "dine-in", "quiet", "family", "date", "casual", "crowded-ok"),
  "area": string or null (e.g. "Uttara", "Dhanmondi", "Gulshan"),
  "keywords": [string] (other important words from the query)
}

Rules:
- If the query mentions a price range like "1000 BDT max for 2 people", set budget_max_bdt to 500 (per person)
- If no area is mentioned, set area to null
- Extract cuisine type from context: "burger place" → "burger", "biryani" → "biryani"
- keywords should capture anything not covered by other fields
- Respond ONLY with JSON, no explanation

Examples:
"Two people dine in range 1000 BDT max" → {"cuisine": null, "budget_max_bdt": 500, "party_size": 2, "vibe": "dine-in", "area": null, "keywords": []}
"Best burger in Uttara" → {"cuisine": "burger", "budget_max_bdt": null, "party_size": null, "vibe": null, "area": "Uttara", "keywords": ["best"]}
"কম ভিড় কিন্তু ভালো খাবার" → {"cuisine": null, "budget_max_bdt": null, "party_size": null, "vibe": "quiet", "area": null, "keywords": ["good food", "less crowded"]}"""


def parse_intent_from_response(raw: str) -> dict:
    """Parse the LLM response into a structured intent dict."""
    try:
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()
        return json.loads(text)
    except (json.JSONDecodeError, ValueError):
        logger.warning("Failed to parse intent: %s", raw[:200])
        return {}


async def parse_user_query(query: str) -> dict:
    """Send user's natural language query to LLM and parse intent."""
    raw = await _call_llm(INTENT_SYSTEM_PROMPT, query, model="haiku", max_tokens=300)
    return parse_intent_from_response(raw)


# Postcode-to-area mapping for Dhaka
AREA_POSTCODES = {
    "uttara": ["1230"],
    "mirpur": ["1216"],
    "dhanmondi": ["1205", "1209"],
    "gulshan": ["1212"],
    "banani": ["1213"],
    "bashundhara": ["1229"],
    "motijheel": ["1000"],
    "mohammadpur": ["1207"],
}

# Reverse mapping
POSTCODE_TO_AREA = {}
for area, codes in AREA_POSTCODES.items():
    for code in codes:
        POSTCODE_TO_AREA[code] = area

# Adjacent areas for "nearby" suggestions
NEARBY_AREAS = {
    "uttara": ["banani", "mirpur"],
    "mirpur": ["uttara", "mohammadpur", "dhanmondi"],
    "dhanmondi": ["mirpur", "mohammadpur", "motijheel"],
    "gulshan": ["banani", "bashundhara"],
    "banani": ["gulshan", "uttara"],
    "bashundhara": ["gulshan", "banani"],
    "motijheel": ["dhanmondi"],
    "mohammadpur": ["dhanmondi", "mirpur"],
}


def _area_to_postcodes(area_name: str | None) -> list[str]:
    """Convert an area name to postcodes."""
    if not area_name:
        return []
    key = area_name.lower().strip()
    return AREA_POSTCODES.get(key, [])


def _nearby_postcodes(area_name: str | None) -> list[str]:
    """Get postcodes for adjacent areas."""
    if not area_name:
        return []
    key = area_name.lower().strip()
    nearby = NEARBY_AREAS.get(key, [])
    codes = []
    for a in nearby:
        codes.extend(AREA_POSTCODES.get(a, []))
    return codes


async def discover_restaurants(
    db: AsyncSession,
    query: str,
    user_postcode: str | None = None,
    limit: int = 3,
    nearby_limit: int = 3,
) -> dict:
    """Main discovery function: NL query → ranked restaurants + nearby."""

    # 1. Parse intent
    intent = await parse_user_query(query)

    # 2. Determine area from intent or user location
    area = intent.get("area")
    postcodes = _area_to_postcodes(area)
    if not postcodes and user_postcode:
        postcodes = [user_postcode]
        area = POSTCODE_TO_AREA.get(user_postcode)

    # 3. Build base query
    base = select(Business).where(Business.enriched == True)

    # Filter by area postcodes
    if postcodes:
        base = base.where(Business.postcode.in_(postcodes))

    # Filter by cuisine/category
    cuisine = intent.get("cuisine")
    if cuisine:
        base = base.where(
            or_(
                Business.categories.ilike(f"%{cuisine}%"),
                Business.business_name.ilike(f"%{cuisine}%"),
            )
        )

    # 4. Rank by rating + review count
    query_stmt = (
        base
        .order_by(
            Business.rating.desc().nullslast(),
            Business.review_count.desc(),
        )
        .limit(limit)
    )

    result = await db.execute(query_stmt)
    main_results = result.scalars().all()

    # 5. Get nearby suggestions
    nearby_results = []
    if area:
        nearby_codes = _nearby_postcodes(area)
        if nearby_codes:
            nearby_stmt = (
                select(Business)
                .where(
                    Business.enriched == True,
                    Business.postcode.in_(nearby_codes),
                )
                .order_by(Business.rating.desc().nullslast(), Business.review_count.desc())
                .limit(nearby_limit)
            )
            nearby_res = await db.execute(nearby_stmt)
            nearby_results = nearby_res.scalars().all()

    # 6. Format response
    def format_business(biz: Business) -> dict:
        meta = biz.meta_data or {}
        review_analysis = meta.get("review_analysis") or {}
        price = meta.get("price_details") or {}

        # Build a 1-line insight from review analysis
        praised = review_analysis.get("top_praised", [])
        insight = praised[0] if praised else None

        return {
            "id": str(biz.id),
            "name": biz.business_name,
            "slug": biz.slug,
            "rating": biz.rating,
            "review_count": biz.review_count,
            "address": biz.address,
            "postcode": biz.postcode,
            "area": POSTCODE_TO_AREA.get(biz.postcode or "", biz.postcode),
            "lat": biz.lat,
            "lng": biz.lng,
            "categories": biz.categories,
            "thumbnail": meta.get("thumbnail") or (biz.cached_data or {}).get("thumbnail"),
            "price_range": price.get("distribution", [{}])[0].get("price") if price.get("distribution") else None,
            "insight": insight,
            "facebook_url": biz.facebook_url,
            "instagram_url": biz.instagram_url,
            "menu_highlights": (meta.get("menu_highlights") or [])[:4],
        }

    return {
        "intent": intent,
        "results": [format_business(b) for b in main_results],
        "nearby": [format_business(b) for b in nearby_results],
        "area": area,
    }
