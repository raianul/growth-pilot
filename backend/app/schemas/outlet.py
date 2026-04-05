from uuid import UUID
from pydantic import BaseModel


class OutletCreate(BaseModel):
    outlet_name: str
    city: str
    address: str | None = None
    google_place_id: str | None = None
    maps_url: str | None = None


class OutletUpdate(BaseModel):
    outlet_name: str | None = None
    city: str | None = None
    address: str | None = None
    google_place_id: str | None = None
    maps_url: str | None = None


class OutletResponse(BaseModel):
    id: UUID
    organization_id: UUID
    outlet_name: str
    city: str
    address: str | None
    google_place_id: str | None
    maps_url: str | None
    model_config = {"from_attributes": True}
