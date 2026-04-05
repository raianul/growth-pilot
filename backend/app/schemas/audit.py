from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class AuditTriggerResponse(BaseModel):
    audit_id: UUID
    status: str

class DimensionResponse(BaseModel):
    dimension: str
    score: int
    weight: float
    is_stale: bool
    raw_data: dict | None = None
    model_config = {"from_attributes": True}

class AuditResponse(BaseModel):
    id: UUID
    week_number: int
    status: str
    total_score: int | None
    score_delta: int | None
    current_phase: str | None = None
    phase_progress: dict | None = None
    created_at: datetime
    completed_at: datetime | None
    dimensions: list[DimensionResponse] = []
    model_config = {"from_attributes": True}

class ScoreHistoryItem(BaseModel):
    week_number: int
    score: int
    dimensions: list[DimensionResponse] = []
