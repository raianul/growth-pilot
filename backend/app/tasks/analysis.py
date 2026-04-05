import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.tasks import celery_app
from app.tasks.db import run_async, task_session
from app.models.audit import WeeklyAudit
from app.models.dimension import AuditDimension
from app.models.mission import Mission
from app.models.organization import Organization
from app.models.outlet import Outlet

logger = logging.getLogger(__name__)

DIMENSION_WEIGHTS = {
    "google_maps": 0.30,
    "website": 0.25,
    "local_authority": 0.20,
    "youtube": 0.15,
    "ai_readiness": 0.10,
}

CHANNEL_DIMENSION = {
    "google_maps": "google_maps",
    "website": "website",
    "social": "local_authority",
    "youtube": "youtube",
    "reddit": "local_authority",
    "local_authority": "local_authority",
}


def _score_google_maps(data: dict | None) -> int:
    """Score 0-100 based on Maps ranking, rating, and review count."""
    if not data:
        return 0
    score = 0
    position = data.get("position")
    if position is not None:
        if position <= 3:
            score += 50
        elif position <= 10:
            score += 30
    rating = data.get("rating") or 0
    if rating >= 4.5:
        score += 30
    elif rating >= 4.0:
        score += 20
    reviews = data.get("reviews") or 0
    if reviews >= 100:
        score += 20
    elif reviews >= 50:
        score += 10
    return min(100, score)


def _score_website(data: dict | None) -> int:
    """Score 0-100 based on content presence and metadata quality."""
    if not data:
        return 0
    score = 0

    # Content quality — use AI assessment if available, else fall back to length check
    quality = data.get("content_quality")
    if quality and isinstance(quality, dict):
        q = quality.get("quality", "low")
        if q == "high":
            score += 30
        elif q == "medium":
            score += 20
        elif q == "low":
            score += 5
    else:
        content = data.get("content") or ""
        if len(content) > 500:
            score += 30

    if data.get("description"):
        score += 15
    links = data.get("links") or []
    if len(links) >= 3:
        score += 15
    # Schema: use the pre-computed flag from firecrawl (checks HTML, not markdown)
    if data.get("has_schema") or "LocalBusiness" in content or "schema.org" in content:
        score += 20
    if data.get("title"):
        score += 10
    # Blog: use pre-computed flag or check links
    if data.get("has_blog") or any("blog" in str(link).lower() for link in links):
        score += 10
    return min(100, score)


def _score_local_authority(data: dict | None) -> int:
    """Score 0-100 based on local mention count and best-of list presence."""
    if not data:
        return 10
    mention_count = data.get("mention_count", 0)
    if mention_count >= 5:
        score = 80
    elif mention_count >= 3:
        score = 60
    elif mention_count >= 1:
        score = 40
    else:
        score = 10
    if data.get("on_best_of_list"):
        score += 20
    return min(100, score)


def _score_youtube(data: dict | None) -> int:
    """Score 0-100 based on video presence and channel ownership."""
    if not data:
        return 10
    video_count = data.get("video_count", 0)
    if video_count >= 5:
        score = 70
    elif video_count >= 2:
        score = 50
    elif video_count >= 1:
        score = 30
    else:
        score = 10
    if data.get("has_own_channel"):
        score += 20
    return min(100, score)


def _compute_ai_readiness(dimensions: dict) -> int:
    """
    Compute AI Readiness score derived from other dimensions' scrape data.

    dimensions: dict keyed by dimension name, each value is a scrape result dict
                with a "data" key containing the raw scraped payload.
    """
    score = 0

    # Check website for Schema markup (uses HTML check from firecrawl)
    website_data = (dimensions.get("website") or {}).get("data") or {}
    content = website_data.get("content", "")
    if website_data.get("has_schema") or "LocalBusiness" in content or "schema.org" in content:
        score += 30

    # Check review keyword quality — use AI analysis if available, else fall back to count
    gm_data = (dimensions.get("google_maps") or {}).get("data") or {}
    review_analysis = gm_data.get("review_analysis") or {}
    review_quality = review_analysis.get("review_quality", "low")
    if review_quality == "high":
        score += 25
    elif review_quality == "medium":
        score += 15
    elif (gm_data.get("reviews") or 0) >= 50:
        score += 10

    # NAP consistency
    gm_title = (gm_data.get("title") or "").lower()
    web_title = (website_data.get("title") or "").lower()
    if gm_title and web_title and (gm_title in web_title or web_title in gm_title):
        score += 25

    # Local authority mentions
    la_data = (dimensions.get("local_authority") or {}).get("data") or {}
    if la_data.get("mention_count", 0) >= 3:
        score += 20

    return min(score, 100)


DIMENSION_SCORERS = {
    "google_maps": _score_google_maps,
    "website": _score_website,
    "local_authority": _score_local_authority,
    "youtube": _score_youtube,
}


async def _save_dimensions_and_score(audit_id: str, dimension_scores: dict, scrape_results: list[dict]) -> dict:
    """Persist AuditDimension rows and the overall WeeklyAudit score."""
    staleness = {r["dimension"]: r.get("is_stale", False) for r in scrape_results}

    weighted_total = 0.0
    for dim, weight in DIMENSION_WEIGHTS.items():
        weighted_total += dimension_scores.get(dim, 0) * weight

    total_score = round(weighted_total)

    async with task_session() as session:
        audit_uuid = uuid.UUID(audit_id)

        # Upsert AuditDimension rows
        for dim, weight in DIMENSION_WEIGHTS.items():
            dim_score = dimension_scores.get(dim, 0)
            is_stale = staleness.get(dim, False)
            # Find raw_data for this dimension
            raw_data = next(
                (r.get("data") for r in scrape_results if r.get("dimension") == dim), None
            )
            dimension = AuditDimension(
                audit_id=audit_uuid,
                dimension=dim,
                score=dim_score,
                weight=weight,
                is_stale=is_stale,
                raw_data=raw_data,
            )
            session.add(dimension)

        # Update audit total score and phase
        result = await session.execute(select(WeeklyAudit).where(WeeklyAudit.id == audit_uuid))
        audit = result.scalar_one_or_none()
        if audit:
            prev_score = audit.total_score or 0
            audit.total_score = total_score
            audit.score_delta = total_score - prev_score
            progress = audit.phase_progress or {}
            progress["scoring"] = "done"
            audit.phase_progress = progress
            audit.current_phase = "scoring"

        await session.commit()

    return {
        "audit_id": audit_id,
        "total_score": total_score,
        "dimension_scores": dimension_scores,
    }


@celery_app.task(name="compute_visibility_score", bind=True, max_retries=0)
def compute_visibility_score(self, scrape_results: list[dict], audit_id: str, outlet_id: str) -> dict:
    """
    Phase 2 entry point — score each dimension 0-100, compute weighted total, save to DB.

    scrape_results: list of dicts from the Phase 1 chord, each with keys
        {data, is_stale, dimension}
    """
    dimension_scores: dict[str, int] = {}
    for result in scrape_results:
        dim = result.get("dimension")
        data = result.get("data")
        scorer = DIMENSION_SCORERS.get(dim)
        if scorer:
            dimension_scores[dim] = scorer(data)

    # Build a dimension lookup for ai_readiness computation
    dimensions_by_name = {r["dimension"]: r for r in scrape_results}

    # Merge review analysis into google_maps raw data
    reviews_result = next((r for r in scrape_results if r.get("dimension") == "reviews"), None)
    if reviews_result and reviews_result.get("data"):
        gm_key = "google_maps"
        if gm_key in dimensions_by_name:
            gm_data = dimensions_by_name[gm_key].get("data") or {}
            gm_data["review_analysis"] = reviews_result["data"].get("analysis", {})
            gm_data["recent_reviews"] = reviews_result["data"].get("reviews", [])[:5]
            dimensions_by_name[gm_key]["data"] = gm_data
            # Also update in scrape_results list so it persists to DB
            for r in scrape_results:
                if r.get("dimension") == gm_key:
                    r["data"] = gm_data
                    break

    ai_readiness_score = _compute_ai_readiness(dimensions_by_name)
    dimension_scores["ai_readiness"] = ai_readiness_score

    # Build ai_readiness raw data with richer fields for frontend display
    website_data = (dimensions_by_name.get("website", {}).get("data") or {})
    gm_data_for_ai = (dimensions_by_name.get("google_maps", {}).get("data") or {})
    review_analysis_for_ai = gm_data_for_ai.get("review_analysis") or {}

    # Add a synthetic scrape result for ai_readiness so it persists with raw_data
    scrape_results = list(scrape_results) + [{
        "dimension": "ai_readiness",
        "data": {
            "has_schema": website_data.get("has_schema"),  # None = could not check, False = missing, True = found
            "review_keywords": ((gm_data_for_ai.get("reviews") or 0) >= 50),
            "review_quality": review_analysis_for_ai.get("review_quality"),  # "high"|"medium"|"low"|None
            "nap_consistent": dimension_scores.get("ai_readiness", 0) >= 25,
            "local_mentions": (dimensions_by_name.get("local_authority", {}).get("data") or {}).get("mention_count", 0),
        },
        "is_stale": False,
    }]

    score_result = run_async(_save_dimensions_and_score(audit_id, dimension_scores, scrape_results))
    score_result["outlet_id"] = outlet_id
    return score_result


async def _load_outlet_with_org(outlet_id: str) -> Outlet | None:
    async with task_session() as session:
        result = await session.execute(
            select(Outlet)
            .options(selectinload(Outlet.organization))
            .where(Outlet.id == uuid.UUID(outlet_id))
        )
        return result.scalar_one_or_none()


async def _save_missions(audit_id: str, outlet_id: str, missions_data: list, dimension_scores: dict | None = None) -> list[dict]:
    # Ensure missions_data is a list of dicts
    if not isinstance(missions_data, list):
        logger.error("missions_data is not a list: %s", type(missions_data))
        return []
    missions_data = [m for m in missions_data if isinstance(m, dict)]
    if dimension_scores is None:
        dimension_scores = {}

    async with task_session() as session:
        saved = []
        for idx, m in enumerate(missions_data):
            channel = m.get("channel", "website")
            impact_score = m.get("impact_score", 5)
            dim_name = CHANNEL_DIMENSION.get(channel, None)
            weight = DIMENSION_WEIGHTS.get(dim_name, 0.15) if dim_name else 0.15
            dim_score = dimension_scores.get(dim_name, 50) if dim_name else 50
            gap_ratio = (100 - dim_score) / 100
            priority_score = impact_score * weight * gap_ratio

            mission = Mission(
                audit_id=uuid.UUID(audit_id),
                outlet_id=uuid.UUID(outlet_id),
                title=m.get("title", ""),
                description=m.get("description", ""),
                channel=channel,
                impact_score=impact_score,
                difficulty=m.get("difficulty", "medium"),
                estimated_minutes=m.get("estimated_minutes", 20),
                status="pending",
                sort_order=idx,
                priority_score=priority_score,
            )
            session.add(mission)
            await session.flush()
            saved.append({
                "mission_id": str(mission.id),
                "title": mission.title,
                "channel": mission.channel,
                "impact_score": mission.impact_score,
                "difficulty": mission.difficulty,
                "estimated_minutes": mission.estimated_minutes,
                "priority_score": mission.priority_score,
            })

        result = await session.execute(
            select(WeeklyAudit).where(WeeklyAudit.id == uuid.UUID(audit_id))
        )
        audit = result.scalar_one_or_none()
        if audit:
            progress = audit.phase_progress or {}
            progress["missions"] = "done"
            audit.phase_progress = progress
            audit.current_phase = "missions"

        await session.commit()
    return saved


@celery_app.task(name="analyze_competitor_gaps", bind=True, max_retries=0)
def analyze_competitor_gaps(self, score_result: dict) -> dict:
    """
    Phase 2b — call Claude Sonnet to identify gaps from dimension scores.

    Returns the analysis dict merged with the incoming score_result so the
    next step in the chain has full context.
    """
    from app.services.claude_ai import analyze_audit_data

    audit_id = score_result["audit_id"]
    outlet_id = score_result.get("outlet_id") or score_result.get("audit_id")  # fallback
    dimension_scores = score_result.get("dimension_scores", {})

    async def _analyze():
        outlet = await _load_outlet_with_org(outlet_id)
        business_name = outlet.organization.business_name if outlet else "Unknown"
        analysis = await analyze_audit_data(business_name, dimension_scores, [])
        return analysis

    try:
        analysis = run_async(_analyze())
    except Exception as exc:
        logger.exception("analyze_competitor_gaps failed: %s", exc)
        analysis = {"gaps": [], "strengths": [], "priority_areas": [], "competitor_advantages": []}

    return {**score_result, "analysis": analysis}


@celery_app.task(name="generate_missions_task", bind=True, max_retries=0)
def generate_missions_task(self, analysis_result: dict) -> dict:
    """
    Phase 2c — call Claude Sonnet to generate 3 missions, save to DB.
    """
    from app.services.claude_ai import generate_missions

    audit_id = analysis_result["audit_id"]
    outlet_id = analysis_result.get("outlet_id") or analysis_result.get("audit_id")
    analysis = analysis_result.get("analysis", {})

    async def _gen():
        outlet = await _load_outlet_with_org(outlet_id)
        business_name = outlet.organization.business_name if outlet else "Unknown"
        brand_voice = outlet.organization.tone_of_voice if outlet else "professional and friendly"
        if not brand_voice:
            brand_voice = "professional and friendly"
        website_url = outlet.organization.website_url if outlet else ""
        missions_data = await generate_missions(business_name, analysis, brand_voice, website_url=website_url)
        dimension_scores = analysis_result.get("dimension_scores", {})
        saved = await _save_missions(audit_id, outlet_id, missions_data, dimension_scores)
        return saved

    try:
        missions = run_async(_gen())
    except Exception as exc:
        logger.exception("generate_missions_task failed: %s", exc)
        missions = []

    return {
        "audit_id": audit_id,
        "outlet_id": outlet_id,
        "missions": missions,
        "total_score": analysis_result.get("total_score", 0),
    }
