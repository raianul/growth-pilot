import uuid

from sqlalchemy import String, Integer, Text, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    audit_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("weekly_audits.id"), index=True)
    outlet_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("outlets.id"), index=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String)
    impact_score: Mapped[int] = mapped_column(Integer)
    difficulty: Mapped[str] = mapped_column(String)
    estimated_minutes: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, default="pending")
    sort_order: Mapped[int] = mapped_column(Integer)
    priority_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    audit: Mapped["WeeklyAudit"] = relationship(back_populates="missions")
    outlet: Mapped["Outlet"] = relationship(back_populates="missions")
    content_drafts: Mapped[list["ContentDraft"]] = relationship(back_populates="mission")
