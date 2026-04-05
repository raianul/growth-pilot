"""Mock responses for dev mode when external API keys are not configured."""

import random


def mock_google_maps(business_name: str, city: str, category: str) -> dict:
    return {
        "place_id": "mock_place_abc123",
        "position": random.randint(1, 8),
        "rating": round(random.uniform(3.8, 4.9), 1),
        "reviews": random.randint(20, 300),
        "title": business_name,
    }


def mock_competitors(business_name: str, city: str, category: str) -> list[dict]:
    names = [f"Best {category.title()} {city}", f"{city} {category.title()} Co", f"The Local {category.title()}"]
    return [
        {
            "place_id": f"mock_comp_{i}",
            "business_name": name,
            "rating": round(random.uniform(3.5, 5.0), 1),
            "reviews": random.randint(30, 500),
            "position": i + 1,
        }
        for i, name in enumerate(names)
    ]


def mock_website(url: str) -> dict:
    return {
        "content": f"# Welcome\nThis is the website at {url}. We offer great products and services to our local community.",
        "title": "Business Website",
        "description": "A great local business serving the community.",
        "links": ["/about", "/services", "/contact", "/blog"],
    }


def mock_local_authority(business_name: str, city: str) -> dict:
    return {
        "mention_count": random.randint(0, 5),
        "sources": [{"title": f"Best gyms in {city}", "url": "https://example.com/best-gyms", "snippet": f"...{business_name} is a popular choice..."}],
        "on_best_of_list": random.choice([True, False]),
    }


def mock_youtube(business_name: str, city: str) -> dict:
    count = random.randint(0, 4)
    return {
        "video_count": count,
        "videos": [
            {"video_id": "mock123", "title": f"Review: {business_name}", "channel": "LocalReviewer", "published_at": "2025-12-01T00:00:00Z", "description": "A review..."}
        ] if count > 0 else [],
        "has_own_channel": False,
    }


def mock_analysis(brand_name: str) -> dict:
    return {
        "gaps": [
            "Low Google Maps review count compared to competitors",
            "No YouTube presence — competitors have review videos",
            "Website lacks structured data markup",
        ],
        "strengths": [
            "Strong Google Maps rating (4.5+)",
            "Active Reddit community mentions",
        ],
        "priority_areas": ["google_maps", "youtube", "website"],
        "competitor_advantages": ["Higher review counts", "Video content presence"],
    }


def mock_missions(brand_name: str) -> list[dict]:
    return [
        {
            "title": "Ask 5 happy customers for Google reviews",
            "description": f"Reach out to your best recent customers and ask them to leave a Google review for {brand_name}. Send them a direct link to make it easy.",
            "channel": "google_maps",
            "impact_score": 9,
            "difficulty": "easy",
            "estimated_minutes": 15,
        },
        {
            "title": "Write a blog post about your specialty",
            "description": f"Create a 300-word blog post highlighting what makes {brand_name} unique. Focus on your top product or service and include local keywords.",
            "channel": "website",
            "impact_score": 7,
            "difficulty": "medium",
            "estimated_minutes": 25,
        },
        {
            "title": "Create a short video tour",
            "description": f"Record a 60-second walkthrough of {brand_name} on your phone. Show your space, team, and best products. Upload to YouTube with local tags.",
            "channel": "youtube",
            "impact_score": 8,
            "difficulty": "medium",
            "estimated_minutes": 20,
        },
    ]


def mock_content(mission_title: str, channel: str, brand_name: str) -> dict:
    templates = {
        "google_maps": {
            "title": "Review Request Message",
            "body": f"Hi! Thank you for choosing {brand_name}. We'd love to hear about your experience! Could you take a moment to leave us a Google review? It really helps other locals find us. Here's the link: [your Google review link]. Thank you so much!",
        },
        "website": {
            "title": f"What Makes {brand_name} Special",
            "body": f"At {brand_name}, we believe in quality above everything else. Since opening our doors, we've been committed to serving our local community with the best products and a personal touch you won't find anywhere else.\n\nWhat sets us apart:\n- Locally sourced ingredients\n- Handcrafted with care\n- A team that knows your name\n\nCome visit us and experience the difference. We're open Monday through Saturday, and we'd love to meet you.",
        },
        "youtube": {
            "title": f"Welcome to {brand_name} | Local Business Tour",
            "body": f"[Video Description]\n\nTake a quick tour of {brand_name}! In this video, we show you our space, introduce our team, and highlight what makes us a favorite in the neighborhood.\n\n📍 Find us at: [Your Address]\n⭐ Leave us a review: [Google Maps Link]\n📱 Follow us: [Social Links]\n\n#localbusiness #{brand_name.replace(' ', '')} #shoplocal",
        },
    }
    return templates.get(channel, {
        "title": f"Content for {mission_title}",
        "body": f"Here's your ready-to-use content for {brand_name}. Customize this to match your brand and post it on {channel}.",
    })
