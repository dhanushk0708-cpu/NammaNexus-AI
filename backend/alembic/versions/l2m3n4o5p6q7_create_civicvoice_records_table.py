"""create civicvoice source records table

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2026-10-29
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "l2m3n4o5p6q7"
down_revision: str | None = "k1l2m3n4o5p6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "civicvoice_source_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=True),
        sa.Column("dedup_key", sa.String(length=64), nullable=False),
        sa.Column("topic", sa.String(length=200), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("dedup_key", name="uq_civicvoice_source_records_dedup_key"),
    )

    op.create_index(
        "ix_civicvoice_source_records_provider",
        "civicvoice_source_records",
        ["provider"],
        unique=False,
    )
    op.create_index(
        "ix_civicvoice_source_records_external_id",
        "civicvoice_source_records",
        ["external_id"],
        unique=False,
    )
    op.create_index(
        "ix_civicvoice_source_records_dedup_key",
        "civicvoice_source_records",
        ["dedup_key"],
        unique=False,
    )
    op.create_index(
        "ix_civicvoice_source_records_topic",
        "civicvoice_source_records",
        ["topic"],
        unique=False,
    )
    op.create_index(
        "ix_civicvoice_source_records_published_at",
        "civicvoice_source_records",
        ["published_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_civicvoice_source_records_published_at", table_name="civicvoice_source_records")
    op.drop_index("ix_civicvoice_source_records_topic", table_name="civicvoice_source_records")
    op.drop_index("ix_civicvoice_source_records_dedup_key", table_name="civicvoice_source_records")
    op.drop_index("ix_civicvoice_source_records_external_id", table_name="civicvoice_source_records")
    op.drop_index("ix_civicvoice_source_records_provider", table_name="civicvoice_source_records")
    op.drop_table("civicvoice_source_records")
