from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class OAuthCredential(Base):
    __tablename__ = "oauth_credentials"

    __table_args__ = (
        UniqueConstraint(
            "channel_connection_id",
            name="uq_oauth_channel_connection",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    channel_connection_id: Mapped[int] = mapped_column(
        ForeignKey("youtube_channels.id", ondelete="CASCADE"),
        nullable=False,
    )

    encrypted_token_json: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    scopes: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )

    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )