"""add routing fields to complaints

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-09-02 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "complaints",
        sa.Column("authority", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "complaints",
        sa.Column("department", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "complaints",
        sa.Column("routing_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("complaints", "routing_reason")
    op.drop_column("complaints", "department")
    op.drop_column("complaints", "authority")
