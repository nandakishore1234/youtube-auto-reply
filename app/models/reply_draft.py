from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from datetime import datetime, timezone

class ReplyDraft(Base):
    __tablename__ = "reply_drafts"

    __table_args__ = (
        UniqueConstraint(
            "comment_id",
            name="uq_reply_draft_comment",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    comment_id: Mapped[int] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    reply_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    intent: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    needs_human_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="pending_approval",
        server_default="pending_approval",
    )

    review_reason: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )
    
    youtube_reply_id: Mapped[str | None] = mapped_column(
    String(255),
    nullable=True,
    )

    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    comment: Mapped["Comment"] = relationship(
        back_populates="draft",
    )