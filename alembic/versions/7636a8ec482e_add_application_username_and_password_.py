"""add application username and password hash

Revision ID: 7636a8ec482e
Revises: 0865a80eb937
Create Date: 2026-10-24 04:30:14.556527

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7636a8ec482e'
down_revision: Union[str, Sequence[str], None] = '0865a80eb937'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Nullable temporarily so existing user records survive.
    op.add_column(
        "users",
        sa.Column("username", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )

    # Give existing users unique temporary usernames.
    op.execute(
        "UPDATE users SET username = 'legacy_user_' || id::text "
        "WHERE username IS NULL"
    )

    op.alter_column(
        "users",
        "username",
        existing_type=sa.String(length=50),
        nullable=False,
    )

    op.create_index(
        "ix_users_username",
        "users",
        ["username"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "username")
