from uuid import UUID
from pydantic import BaseModel

class CompetitorResponse(BaseModel):
    id: UUID
    business_name: str
    google_place_id: str | None
    source: str
    latest_score: int | None
    gap_analysis: dict | None
    model_config = {"from_attributes": True}

class CompetitorSwap(BaseModel):
    business_name: str
    city: str
