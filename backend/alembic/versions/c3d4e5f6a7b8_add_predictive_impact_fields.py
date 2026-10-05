"""add predictive impact fields to complaints

Revision ID: c3d4e5f6a7b8
Revises: b1b2c3d4e5f6
Create Date: 2026-09-01 02:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('complaints', sa.Column('impact_score', sa.Integer(), nullable=True))
    op.add_column('complaints', sa.Column('priority', sa.String(length=20), nullable=True))
    op.add_column('complaints', sa.Column('impact_reason', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('complaints', 'impact_reason')
    op.drop_column('complaints', 'priority')
    op.drop_column('complaints', 'impact_score')
