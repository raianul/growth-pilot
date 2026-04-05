import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Float, ForeignKey, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    outlet_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("outlets.id"), index=True, nullable=True)
    seeded_area_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("seeded_areas.id"), index=True, nullable=True)
    business_name: Mapped[str] = mapped_column(String)
    google_place_id: Mapped[str | None] = mapped_column(String, nullable=True)
    maps_url: Mapped[str | None] = mapped_column(String, nullable=True)
    website_url: Mapped[str | None] = mapped_column(String, nullable=True)
    facebook_page_url: Mapped[str | None] = mapped_column(String, nullable=True)
    instagram_handle: Mapped[str | None] = mapped_column(String, nullable=True)
    area: Mapped[str | None] = mapped_column(String, nullable=True)
    postcode: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String, default="manual")  # manual | auto
    cached_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    gap_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    outlet: Mapped["Outlet"] = relationship(back_populates="competitors")
