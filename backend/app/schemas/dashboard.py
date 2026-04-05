from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.schemas.audit import AuditResponse
from app.schemas.mission import MissionResponse


class DashboardResponse(BaseModel):
    outlet_id: UUID
    outlet_name: str
    organization_name: str
    latest_audit: AuditResponse | None
    active_missions: list[MissionResponse]
    next_audit_at: datetime | None
