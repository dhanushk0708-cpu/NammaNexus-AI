"""add complaint draft fields

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-09-02 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e5f6a7b8c9d0"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "complaints",
        sa.Column("subject", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "complaints",
        sa.Column("complaint_text", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("complaints", "complaint_text")
    op.drop_column("complaints", "subject")
