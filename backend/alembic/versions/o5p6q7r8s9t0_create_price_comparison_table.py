"""create nammaserve price comparisons table

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-10-29 23:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "o5p6q7r8s9t0"
down_revision: str | None = "n4o5p6q7r8s9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Use JSONB for PostgreSQL, standard JSON for others (e.g. SQLite test runners)
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    json_col = postgresql.JSONB(astext_type=sa.Text()) if is_postgres else sa.JSON()

    op.create_table(
        "nammaserve_price_comparisons",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("record_hash", sa.String(length=64), nullable=False),
        sa.Column("source_platform", sa.String(length=50), nullable=False),
        sa.Column("service_category", sa.String(length=100), nullable=False),
        sa.Column("service_name", sa.String(length=200), nullable=False),
        sa.Column("provider_name", sa.String(length=200), nullable=False),
        sa.Column("published_price", sa.String(length=100), nullable=False),
        sa.Column("currency", sa.String(length=10), server_default="INR", nullable=False),
        sa.Column("price_type", sa.String(length=30), nullable=False),
        sa.Column("price_unit", sa.String(length=100), nullable=True),
        sa.Column("price_scope", sa.Text(), nullable=True),
        sa.Column("geographic_scope", sa.String(length=255), nullable=False),
        sa.Column("source_url", sa.String(length=500), nullable=False),
        sa.Column("source_checked_date", sa.String(length=20), nullable=False),
        sa.Column("verification_status", sa.String(length=50), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("price_min", sa.Float(), nullable=True),
        sa.Column("price_max", sa.Float(), nullable=True),
        sa.Column("is_locality_specific", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("raw_record", json_col, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("record_hash", name="uq_price_comparisons_record_hash"),
    )
    op.create_index("ix_price_comparisons_record_hash", "nammaserve_price_comparisons", ["record_hash"], unique=True)
    op.create_index("ix_price_comparisons_platform", "nammaserve_price_comparisons", ["source_platform"], unique=False)
    op.create_index("ix_price_comparisons_category", "nammaserve_price_comparisons", ["service_category"], unique=False)
    op.create_index("ix_price_comparisons_service_name", "nammaserve_price_comparisons", ["service_name"], unique=False)
    op.create_index("ix_price_comparisons_price_type", "nammaserve_price_comparisons", ["price_type"], unique=False)
    op.create_index("ix_price_comparisons_ver_status", "nammaserve_price_comparisons", ["verification_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_price_comparisons_ver_status", table_name="nammaserve_price_comparisons")
    op.drop_index("ix_price_comparisons_price_type", table_name="nammaserve_price_comparisons")
    op.drop_index("ix_price_comparisons_service_name", table_name="nammaserve_price_comparisons")
    op.drop_index("ix_price_comparisons_category", table_name="nammaserve_price_comparisons")
    op.drop_index("ix_price_comparisons_platform", table_name="nammaserve_price_comparisons")
    op.drop_index("ix_price_comparisons_record_hash", table_name="nammaserve_price_comparisons")
    op.drop_table("nammaserve_price_comparisons")
