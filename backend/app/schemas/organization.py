from uuid import UUID
from pydantic import BaseModel


class OrganizationCreate(BaseModel):
    business_name: str
    website_url: str
    category: str


class OrganizationUpdate(BaseModel):
    business_name: str | None = None
    website_url: str | None = None
    category: str | None = None
    tone_of_voice: str | None = None
    brand_keywords: list[str] | None = None


class OrganizationResponse(BaseModel):
    id: UUID
    business_name: str
    website_url: str
    category: str
    tone_of_voice: str | None
    brand_keywords: list[str] | None
    model_config = {"from_attributes": True}
