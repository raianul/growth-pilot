import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def slugify(name: str) -> str:
    """Convert business name to URL slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug if slug else str(uuid.uuid4())[:8]


async def generate_unique_slug(session: AsyncSession, name: str, model_class: type) -> str:
    """Generate a unique slug, auto-incrementing on collision."""
    base_slug = slugify(name)

    # Check if base slug is available
    result = await session.execute(
        select(model_class).where(model_class.slug == base_slug).limit(1)
    )
    if not result.scalar_one_or_none():
        return base_slug

    # Collision — try with incrementing suffix
    counter = 2
    while True:
        candidate = f"{base_slug}-{counter}"
        result = await session.execute(
            select(model_class).where(model_class.slug == candidate).limit(1)
        )
        if not result.scalar_one_or_none():
            return candidate
        counter += 1
