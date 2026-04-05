import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SoftLead(Base):
    __tablename__ = "soft_leads"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str | None] = mapped_column(String, nullable=True)
    email: Mapped[str] = mapped_column(String)
    whatsapp_number: Mapped[str] = mapped_column(String)
    google_place_id: Mapped[str] = mapped_column(String, index=True)
    audit_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("weekly_audits.id"), nullable=True)
    area: Mapped[str | None] = mapped_column(String, nullable=True)
    converted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
