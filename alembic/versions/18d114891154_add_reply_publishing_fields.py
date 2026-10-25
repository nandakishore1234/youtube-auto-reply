"""add reply publishing fields

Revision ID: 18d114891154
Revises: 4d2c8f91a6b3
Create Date: 2026-10-24 21:04:58.042100

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '18d114891154'
down_revision: Union[str, Sequence[str], None] = '4d2c8f91a6b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        "reply_drafts",
        sa.Column("youtube_reply_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "reply_drafts",
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reply_drafts", "published_at")
    op.drop_column("reply_drafts", "youtube_reply_id")
