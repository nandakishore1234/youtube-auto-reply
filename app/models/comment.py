from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Comment(Base):
    __tablename__ = "comments"

    __table_args__ = (
        UniqueConstraint(
            "youtube_channel_id",
            "youtube_comment_id",
            name="uq_channel_youtube_comment",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    youtube_channel_id: Mapped[int] = mapped_column(
        ForeignKey("youtube_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    youtube_comment_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    youtube_video_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    parent_youtube_comment_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    author_display_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="received",
        server_default="received",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    draft: Mapped["ReplyDraft | None"] = relationship(
        back_populates="comment",
        cascade="all, delete-orphan",
        uselist=False,
    )