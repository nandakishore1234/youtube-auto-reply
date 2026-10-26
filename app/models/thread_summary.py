from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ThreadSummary(Base):
    __tablename__ = "thread_summaries"

    __table_args__ = (
        UniqueConstraint(
            "youtube_channel_id",
            "root_youtube_comment_id",
            name="uq_thread_summary_channel_root",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    youtube_channel_id: Mapped[int] = mapped_column(
        ForeignKey("youtube_channels.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    root_youtube_comment_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )

    summarized_through_comment_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
