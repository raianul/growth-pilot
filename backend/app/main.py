from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1 import router as v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # In dev mode, auto-create all tables on startup
    if settings.dev_mode:
        from app.core.database import engine
        from app.models.base import Base
        import app.models  # noqa: F401 — register all models

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    yield


def create_app() -> FastAPI:
    app = FastAPI(title="GrowthPilot API", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.app_url, settings.landing_url, settings.kothaykhabo_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router, prefix="/api/v1")

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
