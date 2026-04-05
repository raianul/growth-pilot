from fastapi import APIRouter

from app.core.config import settings
from app.api.v1.organizations import router as organizations_router
from app.api.v1.outlets import router as outlets_router
from app.api.v1.audits import router as audits_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.missions import router as missions_router
from app.api.v1.competitors import router as competitors_router
from app.api.v1.billing import router as billing_router
from app.api.v1.free_audit import router as free_audit_router
from app.api.v1.businesses import router as businesses_router

router = APIRouter()
router.include_router(organizations_router)
router.include_router(outlets_router)
router.include_router(audits_router)
router.include_router(dashboard_router)
router.include_router(missions_router)
router.include_router(competitors_router)
router.include_router(billing_router)
router.include_router(free_audit_router)
router.include_router(businesses_router)

if settings.dev_mode:
    from app.api.v1.dev import router as dev_router
    router.include_router(dev_router)
