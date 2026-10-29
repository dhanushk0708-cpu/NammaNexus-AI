"""add Phase B research provenance fields

Revision ID: j0k1l2m3n4
Revises: i9j0k1l2m3n4
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "j0k1l2m3n4"
down_revision: str | None = "i9j0k1l2m3n4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("service_prices", sa.Column("research_record_id", sa.String(length=100), nullable=True))
    op.add_column("service_prices", sa.Column("comparison_group", sa.String(length=100), nullable=True))
    op.add_column("service_prices", sa.Column("comparability_label", sa.String(length=40), nullable=True))
    op.add_column("service_prices", sa.Column("comparability_reason", sa.Text(), nullable=True))
    op.create_index("ix_service_prices_research_record_id", "service_prices", ["research_record_id"], unique=True)
    op.create_index("ix_service_prices_comparison_group", "service_prices", ["comparison_group"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_service_prices_comparison_group", table_name="service_prices")
    op.drop_index("ix_service_prices_research_record_id", table_name="service_prices")
    op.drop_column("service_prices", "comparability_reason")
    op.drop_column("service_prices", "comparability_label")
    op.drop_column("service_prices", "comparison_group")
    op.drop_column("service_prices", "research_record_id")
