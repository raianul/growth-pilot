import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class WeeklyAudit(Base):
    __tablename__ = "weekly_audits"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    outlet_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("outlets.id"), index=True, nullable=True)
    google_place_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    is_free_audit: Mapped[bool] = mapped_column(Boolean, default=False)
    week_number: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, default="pending")
    current_phase: Mapped[str | None] = mapped_column(String, nullable=True)
    total_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    phase_progress: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    outlet: Mapped["Outlet"] = relationship(back_populates="audits")
    dimensions: Mapped[list["AuditDimension"]] = relationship(back_populates="audit")
    missions: Mapped[list["Mission"]] = relationship(back_populates="audit")
