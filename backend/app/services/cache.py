import json
import logging
from dataclasses import dataclass
from typing import Any, Callable

from app.core.redis import redis_client

logger = logging.getLogger(__name__)

CACHE_TTLS = {
    "serpapi": 7 * 24 * 3600,      # 7 days
    "firecrawl": 14 * 24 * 3600,   # 14 days
    "otterly": 7 * 24 * 3600,
    "reddit": 7 * 24 * 3600,
    "youtube": 7 * 24 * 3600,
}


@dataclass
class ScrapedData:
    data: Any
    is_stale: bool


async def scrape_with_fallback(
    provider: str,
    brand_id: str,
    scrape_fn: Callable,
    max_retries: int = 3,
) -> ScrapedData:
    cache_key = f"api:{provider}:{brand_id}"

    last_error = None
    for attempt in range(max_retries):
        try:
            data = await scrape_fn()
            await redis_client.set(
                cache_key,
                json.dumps(data) if not isinstance(data, str) else data,
                ex=CACHE_TTLS.get(provider, 7 * 24 * 3600),
            )
            return ScrapedData(data=data, is_stale=False)
        except Exception as e:
            last_error = e
            logger.warning(
                "Scrape attempt %d/%d failed for %s:%s — %s",
                attempt + 1, max_retries, provider, brand_id, e,
            )

    logger.error(
        "All %d scrape attempts failed for %s:%s — falling back to cache",
        max_retries, provider, brand_id,
    )
    cached = await redis_client.get(cache_key)
    if cached:
        try:
            data = json.loads(cached)
        except json.JSONDecodeError:
            data = cached
        return ScrapedData(data=data, is_stale=True)

    return ScrapedData(data=None, is_stale=True)
