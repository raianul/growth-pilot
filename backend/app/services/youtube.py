import logging

import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

httpx_client = httpx.AsyncClient(timeout=30.0)
YT_API_BASE = "https://www.googleapis.com/youtube/v3"


async def _get_video_stats(video_ids: list[str]) -> dict[str, dict]:
    """Fetch view counts for a batch of videos. Returns {video_id: {views, likes}}."""
    if not video_ids:
        return {}
    response = await httpx_client.get(
        f"{YT_API_BASE}/videos",
        params={
            "part": "statistics",
            "id": ",".join(video_ids),
            "key": settings.youtube_api_key,
        },
    )
    response.raise_for_status()
    data = response.json()
    stats = {}
    for item in data.get("items", []):
        s = item.get("statistics", {})
        stats[item["id"]] = {
            "views": int(s.get("viewCount", 0)),
            "likes": int(s.get("likeCount", 0)),
        }
    return stats


async def _get_channel_stats(channel_ids: list[str]) -> dict[str, dict]:
    """Fetch subscriber counts for a batch of channels. Returns {channel_id: {subscribers}}."""
    if not channel_ids:
        return {}
    response = await httpx_client.get(
        f"{YT_API_BASE}/channels",
        params={
            "part": "statistics",
            "id": ",".join(channel_ids),
            "key": settings.youtube_api_key,
        },
    )
    response.raise_for_status()
    data = response.json()
    stats = {}
    for item in data.get("items", []):
        s = item.get("statistics", {})
        stats[item["id"]] = {
            "subscribers": int(s.get("subscriberCount", 0)),
        }
    return stats


async def scrape_youtube(business_name: str, city: str) -> dict:
    if settings.dev_mode and not settings.youtube_api_key:
        from app.services.mock import mock_youtube
        return mock_youtube(business_name, city)

    try:
        # Step 1: Search for videos
        response = await httpx_client.get(
            f"{YT_API_BASE}/search",
            params={
                "part": "snippet",
                "q": f"{business_name} {city}",
                "type": "video",
                "maxResults": 10,
                "key": settings.youtube_api_key,
            },
        )
        response.raise_for_status()
        data = response.json()

        name_lower = business_name.lower()
        all_videos = []
        video_ids = []
        channel_ids = set()

        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            title = snippet.get("title", "")
            description = snippet.get("description", "")[:300]
            video_id = item.get("id", {}).get("videoId")
            channel_id = snippet.get("channelId", "")

            video = {
                "video_id": video_id,
                "title": title,
                "channel": snippet.get("channelTitle"),
                "channel_id": channel_id,
                "published_at": snippet.get("publishedAt"),
                "description": description,
                "confirmed": name_lower in title.lower() or name_lower in description.lower(),
                "views": 0,
                "likes": 0,
                "channel_subscribers": 0,
            }
            all_videos.append(video)
            if video_id:
                video_ids.append(video_id)
            if channel_id:
                channel_ids.add(channel_id)

        # Step 2: Get video stats (views, likes) — 1 API call for all videos
        try:
            video_stats = await _get_video_stats(video_ids)
            for video in all_videos:
                stats = video_stats.get(video["video_id"], {})
                video["views"] = stats.get("views", 0)
                video["likes"] = stats.get("likes", 0)
        except Exception:
            pass

        # Step 3: Get channel stats (subscribers) — 1 API call for all channels
        try:
            channel_stats = await _get_channel_stats(list(channel_ids))
            for video in all_videos:
                stats = channel_stats.get(video.get("channel_id", ""), {})
                video["channel_subscribers"] = stats.get("subscribers", 0)
        except Exception:
            pass

        # Sort: confirmed first, then by views (highest first)
        confirmed = sorted(
            [v for v in all_videos if v["confirmed"]],
            key=lambda v: v["views"],
            reverse=True,
        )
        possible = sorted(
            [v for v in all_videos if not v["confirmed"]],
            key=lambda v: v["views"],
            reverse=True,
        )

        # Step 4: Check if the business has its own YouTube channel
        has_own_channel = False
        channel_name = None
        try:
            ch_response = await httpx_client.get(
                f"{YT_API_BASE}/search",
                params={
                    "part": "snippet",
                    "q": business_name,
                    "type": "channel",
                    "maxResults": 3,
                    "key": settings.youtube_api_key,
                },
            )
            ch_response.raise_for_status()
            ch_data = ch_response.json()

            for item in ch_data.get("items", []):
                title = item.get("snippet", {}).get("title", "")
                if name_lower in title.lower() or title.lower() in name_lower:
                    has_own_channel = True
                    channel_name = title
                    break
        except Exception:
            pass

        return {
            "video_count": len(confirmed),
            "videos": confirmed + possible,
            "confirmed_count": len(confirmed),
            "possible_count": len(possible),
            "has_own_channel": has_own_channel,
            "channel_name": channel_name,
            "error": None,
        }
    except Exception as e:
        logger.error("Failed to scrape YouTube for %s: %s", business_name, e)
        return {
            "video_count": None,  # None = could not check
            "videos": [],
            "confirmed_count": None,
            "possible_count": None,
            "has_own_channel": None,
            "channel_name": None,
            "error": str(e),
        }
