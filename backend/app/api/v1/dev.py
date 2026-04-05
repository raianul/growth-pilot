"""Dev-only endpoints. Only available when DEV_MODE=true."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.user import UserProfile
from app.models.organization import Organization
from app.models.outlet import Outlet
from app.models.audit import WeeklyAudit
from app.models.dimension import AuditDimension
from app.models.mission import Mission
from app.models.content import ContentDraft
from app.models.competitor import Competitor
from app.tasks.analysis import CHANNEL_DIMENSION, DIMENSION_WEIGHTS

router = APIRouter(prefix="/dev", tags=["dev"])


@router.post("/seed")
async def seed_demo_data(
    user: UserProfile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create Fitex gym with 2 outlets, competing against McFit, John Reed, and PureGym."""
    if not settings.dev_mode:
        raise HTTPException(status_code=404)

    # Check if org already exists
    org_result = await db.execute(
        select(Organization).where(Organization.user_id == user.id)
    )
    org = org_result.scalar_one_or_none()

    if org is None:
        org = Organization(
            user_id=user.id,
            business_name="FitX",
            website_url="https://www.fitx.de",
            category="gym",
            tone_of_voice="energetic",
            brand_keywords=["fitness", "gym", "workout", "affordable", "24/7"],
        )
        db.add(org)
        await db.flush()
    else:
        # Update existing org (dev auth creates a placeholder)
        org.business_name = "FitX"
        org.website_url = "https://www.fitx.de"
        org.category = "gym"
        org.tone_of_voice = "energetic"
        org.brand_keywords = ["fitness", "gym", "workout", "affordable", "24/7"]
        await db.flush()

    outlet_result = await db.execute(
        select(Outlet).where(Outlet.organization_id == org.id)
    )
    if outlet_result.scalars().first():
        return {"message": "Demo data already exists", "organization": org.business_name}

    # --- Outlet 1: FitX Kreuzberg ---
    outlet_1 = Outlet(
        organization_id=org.id,
        outlet_name="FitX Kreuzberg",
        city="Berlin",
        address="Kottbusser Damm 22, 10967 Berlin",
        google_place_id="ChIJN1t_tDeuEmsRUsoyG83frY4",
    )
    db.add(outlet_1)
    await db.flush()

    # Competitors for Kreuzberg
    for i, (name, score, advantage) in enumerate([
        ("McFit Kreuzberg", 78, "2x more Google reviews (1,200+)"),
        ("John Reed Kreuzberg", 72, "Strong Instagram presence with 15K followers"),
        ("PureGym Berlin Mitte", 65, "Better YouTube content — gym tour videos"),
    ]):
        db.add(Competitor(
            outlet_id=outlet_1.id,
            business_name=name,
            google_place_id=f"comp_kreuzberg_{i}",
            source="auto",
            latest_score=score,
            gap_analysis={"advantage": advantage},
        ))

    # Completed audit for Kreuzberg
    audit_1 = WeeklyAudit(
        outlet_id=outlet_1.id,
        week_number=1,
        status="completed",
        total_score=62,
        score_delta=None,
        current_phase=None,
        phase_progress={
            "google_maps": "done", "website": "done", "local_authority": "done",
            "youtube": "done", "ai_readiness": "done", "scoring": "done",
            "analysis": "done", "missions": "done", "content_0": "done",
            "content_1": "done", "content_2": "done",
        },
        completed_at=datetime.now(timezone.utc),
    )
    db.add(audit_1)
    await db.flush()

    # Dimensions for Kreuzberg
    dimensions_1 = [
        ("google_maps", 70, 0.30, {"position": 3, "rating": 4.3, "reviews": 487, "title": "FitX Kreuzberg"}),
        ("website", 55, 0.25, {"title": "FitX - Dein Fitnessstudio", "description": "Fitness ab 9,99€/Monat", "content": "...", "links": ["/studios", "/kurse", "/preise", "/app"]}),
        ("local_authority", 60, 0.20, {"mention_count": 3, "sources": [{"title": "Best Budget Gyms in Berlin 2026", "url": "https://mitvergnuegen.com/best-gyms", "snippet": "FitX offers affordable 24/7 access"}], "on_best_of_list": True}),
        ("youtube", 25, 0.15, {"video_count": 2, "videos": [{"title": "FitX Berlin Review", "channel": "FitnessReviewer"}]}),
        ("ai_readiness", 45, 0.10, {"has_schema": False, "review_keywords": True, "nap_consistent": True, "local_mentions": 3}),
    ]
    for dim_name, score, weight, raw_data in dimensions_1:
        db.add(AuditDimension(
            audit_id=audit_1.id, dimension=dim_name,
            score=score, weight=weight, is_stale=False, raw_data=raw_data,
        ))

    # Missions for Kreuzberg
    missions_kreuzberg = [
        {
            "title": "Reply to 10 recent Google reviews",
            "description": "McFit has 2x your reviews. You can't match volume overnight, but you CAN stand out by replying to every review — positive and negative. Go to Google Maps, reply to your 10 most recent reviews with a personal thank-you or helpful response.",
            "channel": "google_maps",
            "impact_score": 9,
            "difficulty": "easy",
            "estimated_minutes": 20,
            "content_title": "Google Review Reply Templates",
            "content_body": "POSITIVE REVIEW REPLY:\nHey [Name]! 💪 Thanks for the awesome review — we love having you at FitX Kreuzberg! Keep crushing those workouts. See you on the gym floor!\n\nNEGATIVE REVIEW REPLY:\nHi [Name], thanks for your honest feedback. We're sorry about [issue]. We've flagged this with our team and would love to make it right. Drop by the front desk next time and ask for the manager — we'll sort it out. 🙏\n\nNEUTRAL REVIEW REPLY:\nThanks for checking us out, [Name]! Glad you stopped by FitX Kreuzberg. If there's anything we can do to make your experience even better, let us know. See you soon! 🏋️",
        },
        {
            "title": "Post a 'Day in the Life at FitX' Instagram Reel",
            "description": "John Reed beats you on social media with 15K followers. Create a 30-60 second Reel showing the gym atmosphere — morning rush, equipment in action, a trainer helping someone, the vibe. Post to Instagram and cross-post to TikTok.",
            "channel": "social",
            "impact_score": 8,
            "difficulty": "medium",
            "estimated_minutes": 25,
            "content_title": "Instagram Reel Script + Caption",
            "content_body": "REEL SCRIPT (30-60 sec):\n[0-5s] Wide shot of gym floor at golden hour, upbeat music\n[5-15s] Quick cuts: someone deadlifting, spinning class energy, stretching zone\n[15-25s] Trainer high-fiving a member after a set\n[25-30s] End card: 'FitX Kreuzberg — ab 9,99€/Monat'\n\nCAPTION:\nThis is what 6 AM looks like at FitX Kreuzberg 🌅💪\n\nNo contracts. No excuses. Just results.\n\n📍 Kottbusser Damm 22\n🕐 24/7 geöffnet\n💰 Ab 9,99€/Monat\n\n#FitXBerlin #KreuzbergFitness #GymLife #BerlinWorkout #FitnessMotivation #24HourGym",
        },
        {
            "title": "Create a YouTube gym tour video",
            "description": "PureGym has gym tour videos that rank on YouTube — you don't. Record a 2-3 minute walkthrough of FitX Kreuzberg showing all areas: cardio, free weights, machines, group fitness room, locker rooms. This is a one-time effort that drives traffic for months.",
            "channel": "youtube",
            "impact_score": 8,
            "difficulty": "medium",
            "estimated_minutes": 30,
            "content_title": "YouTube Video Title + Description",
            "content_body": "TITLE:\nFitX Kreuzberg Gym Tour 2026 | Full Walkthrough 🏋️ Berlin's Best Budget Gym?\n\nDESCRIPTION:\nTake a full tour of FitX Kreuzberg! In this video we walk through every area of the gym — cardio zone, free weights, machines, group fitness room, and more.\n\n🏷️ Membership starts at just 9.99€/month\n📍 Kottbusser Damm 22, 10967 Berlin\n🕐 Open 24/7\n🌐 https://www.fitx.de\n\nFitX is one of Germany's most popular budget gym chains. This Kreuzberg location features:\n✅ Full free weights area with platforms\n✅ Modern cardio machines\n✅ Group fitness classes included\n✅ Clean locker rooms & showers\n✅ No long-term contracts\n\nThinking about joining? Drop by for a free trial!\n\nTAGS: FitX Berlin, gym tour Berlin, Kreuzberg gym, budget gym Germany, FitX review, best gym Berlin 2026, fitness Berlin\n\n#FitX #GymTour #BerlinFitness #Kreuzberg",
        },
    ]

    seed_dimension_scores = {
        "google_maps": 70,
        "website": 55,
        "local_authority": 60,
        "youtube": 25,
        "ai_readiness": 45,
    }

    for i, m in enumerate(missions_kreuzberg):
        channel = m["channel"]
        impact_score = m["impact_score"]
        dim_name = CHANNEL_DIMENSION.get(channel, None)
        weight = DIMENSION_WEIGHTS.get(dim_name, 0.15) if dim_name else 0.15
        dim_score = seed_dimension_scores.get(dim_name, 50) if dim_name else 50
        priority_score = impact_score * weight * (100 - dim_score) / 100

        mission = Mission(
            audit_id=audit_1.id, outlet_id=outlet_1.id,
            title=m["title"], description=m["description"],
            channel=channel, impact_score=impact_score,
            difficulty=m["difficulty"], estimated_minutes=m["estimated_minutes"],
            status="pending", sort_order=i + 1,
            priority_score=priority_score,
        )
        db.add(mission)
        await db.flush()
        db.add(ContentDraft(
            mission_id=mission.id, channel=m["channel"],
            title=m["content_title"], body=m["content_body"], copy_count=0,
        ))

    # --- Outlet 2: FitX Mitte (no audit yet — empty state) ---
    outlet_2 = Outlet(
        organization_id=org.id,
        outlet_name="FitX Mitte",
        city="Berlin",
        address="Alexanderplatz 1, 10178 Berlin",
        google_place_id="ChIJAVkDPzdOqEcRcDteW0YgIQQ",
    )
    db.add(outlet_2)

    await db.commit()

    return {
        "message": "Demo data created — FitX with 2 outlets",
        "organization": org.business_name,
        "outlets": [
            {"name": outlet_1.outlet_name, "id": str(outlet_1.id), "status": "audit complete, score 62"},
            {"name": outlet_2.outlet_name, "id": str(outlet_2.id), "status": "no audit yet"},
        ],
    }
