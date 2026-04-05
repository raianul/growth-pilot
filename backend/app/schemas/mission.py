from uuid import UUID
from pydantic import BaseModel, Field

class MissionResponse(BaseModel):
    id: UUID
    title: str
    description: str
    channel: str
    impact_score: int
    difficulty: str
    estimated_minutes: int
    status: str
    sort_order: int
    priority_score: float | None = None
    model_config = {"from_attributes": True}

class MissionStatusUpdate(BaseModel):
    status: str  # active | completed | skipped

class ContentDraftResponse(BaseModel):
    id: UUID
    channel: str
    title: str
    body: str
    metadata: dict | None = Field(None, validation_alias="extra_metadata")
    copy_count: int
    model_config = {"from_attributes": True, "populate_by_name": True}
