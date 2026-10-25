"""add channel thumbnail url

Revision ID: 4d2c8f91a6b3
Revises: 7636a8ec482e
Create Date: 2026-10-24 20:41:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4d2c8f91a6b3"
down_revision: Union[str, Sequence[str], None] = "7636a8ec482e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "youtube_channels",
        sa.Column("thumbnail_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("youtube_channels", "thumbnail_url")
