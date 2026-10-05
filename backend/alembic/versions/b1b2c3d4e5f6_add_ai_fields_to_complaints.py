"""add AI fields to complaints

Revision ID: b1b2c3d4e5f6
Revises: e70b7b3f7c2c
Create Date: 2026-09-01 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "e70b7b3f7c2c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "complaints",
        sa.Column("confidence", sa.Float(), nullable=True),
    )
    op.add_column(
        "complaints",
        sa.Column("severity", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "complaints",
        sa.Column("visual_explanation", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("complaints", "visual_explanation")
    op.drop_column("complaints", "severity")
    op.drop_column("complaints", "confidence")
