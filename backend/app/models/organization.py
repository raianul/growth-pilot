import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("user_profiles.id"), unique=True, index=True)
    business_name: Mapped[str] = mapped_column(String)
    website_url: Mapped[str] = mapped_column(String)
    category: Mapped[str] = mapped_column(String)
    tone_of_voice: Mapped[str | None] = mapped_column(String, nullable=True)
    brand_keywords: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["UserProfile"] = relationship(back_populates="organization")
    outlets: Mapped[list["Outlet"]] = relationship(back_populates="organization")
