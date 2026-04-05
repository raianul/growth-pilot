import uuid

from sqlalchemy import String, Integer, Text, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class ContentDraft(Base):
    __tablename__ = "content_drafts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    mission_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("missions.id"), index=True)
    channel: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    extra_metadata: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    copy_count: Mapped[int] = mapped_column(Integer, default=0)

    mission: Mapped["Mission"] = relationship(back_populates="content_drafts")
