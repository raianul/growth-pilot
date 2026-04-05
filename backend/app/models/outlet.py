import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Outlet(Base):
    __tablename__ = "outlets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), index=True)
    outlet_name: Mapped[str] = mapped_column(String)
    city: Mapped[str] = mapped_column(String)
    address: Mapped[str | None] = mapped_column(String, nullable=True)
    google_place_id: Mapped[str | None] = mapped_column(String, nullable=True)
    maps_url: Mapped[str | None] = mapped_column(String, nullable=True)
    facebook_page_url: Mapped[str | None] = mapped_column(String, nullable=True)
    instagram_handle: Mapped[str | None] = mapped_column(String, nullable=True)
    area: Mapped[str | None] = mapped_column(String, nullable=True)  # e.g. "mirpur-10", "dhanmondi"
    next_audit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    organization: Mapped["Organization"] = relationship(back_populates="outlets")
    audits: Mapped[list["WeeklyAudit"]] = relationship(back_populates="outlet")
    competitors: Mapped[list["Competitor"]] = relationship(back_populates="outlet")
    missions: Mapped[list["Mission"]] = relationship(back_populates="outlet")
