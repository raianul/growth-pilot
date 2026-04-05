import uuid

from sqlalchemy import String, Integer, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class AuditDimension(Base):
    __tablename__ = "audit_dimensions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    audit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("weekly_audits.id"), index=True)
    dimension: Mapped[str] = mapped_column(String)
    score: Mapped[int] = mapped_column(Integer)
    weight: Mapped[float] = mapped_column(Float)
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    audit: Mapped["WeeklyAudit"] = relationship(back_populates="dimensions")
