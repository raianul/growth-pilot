"""Database utilities for Celery tasks.

Celery tasks run in sync threads with their own event loops.
Each operation gets a fresh engine + session to avoid asyncpg
connection pool conflicts across concurrent tasks.
"""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


@asynccontextmanager
async def task_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a short-lived engine + session for a single task DB operation."""
    engine = create_async_engine(settings.database_url, pool_size=1, max_overflow=0)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


def run_async(coro) -> Any:
    """Run async coroutine from a sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
