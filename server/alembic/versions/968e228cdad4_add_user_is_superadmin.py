"""add_user_is_superadmin

Revision ID: 968e228cdad4
Revises: c46a85b14c74
Create Date: 2026-11-18 16:16:59.274423

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "968e228cdad4"
down_revision: Union[str, Sequence[str], None] = "c46a85b14c74"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_superadmin",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_superadmin")
