"""create civicvoice analysis records table

Revision ID: m3n4o5p6q7r8
Revises: l2m3n4o5p6q7
Create Date: 2026-10-29
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "m3n4o5p6q7r8"
down_revision: str | None = "l2m3n4o5p6q7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "civicvoice_analysis_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("source_record_id", sa.String(length=36), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("sentiment", sa.String(length=20), nullable=True),
        sa.Column("content_intent", sa.String(length=40), nullable=True),
        sa.Column("confidence", sa.String(length=20), nullable=False, server_default="medium"),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("detected_language", sa.String(length=20), nullable=True),
        sa.Column("has_complaint", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("extracted_complaint", sa.Text(), nullable=True),
        sa.Column("has_suggestion", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("extracted_suggestion", sa.Text(), nullable=True),
        sa.Column("theme_id", sa.String(length=50), nullable=True),
        sa.Column("theme_label", sa.String(length=100), nullable=True),
        sa.Column("analysis_method", sa.String(length=50), nullable=False, server_default="rule_based_multilingual"),
        sa.Column("analysis_version", sa.String(length=20), nullable=False, server_default="v1.0"),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["source_record_id"],
            ["civicvoice_source_records.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_civicvoice_analysis_records_source_record_id",
        "civicvoice_analysis_records",
        ["source_record_id"],
        unique=False,
    )
    op.create_index(
        "ix_civicvoice_analysis_records_category",
        "civicvoice_analysis_records",
        ["category"],
        unique=False,
    )
    op.create_index(
        "ix_civicvoice_analysis_records_sentiment",
        "civicvoice_analysis_records",
        ["sentiment"],
        unique=False,
    )
    op.create_index(
        "ix_civicvoice_analysis_records_has_complaint",
        "civicvoice_analysis_records",
        ["has_complaint"],
        unique=False,
    )
    op.create_index(
        "ix_civicvoice_analysis_records_has_suggestion",
        "civicvoice_analysis_records",
        ["has_suggestion"],
        unique=False,
    )
    op.create_index(
        "ix_civicvoice_analysis_records_theme_id",
        "civicvoice_analysis_records",
        ["theme_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_civicvoice_analysis_records_theme_id", table_name="civicvoice_analysis_records")
    op.drop_index("ix_civicvoice_analysis_records_has_suggestion", table_name="civicvoice_analysis_records")
    op.drop_index("ix_civicvoice_analysis_records_has_complaint", table_name="civicvoice_analysis_records")
    op.drop_index("ix_civicvoice_analysis_records_sentiment", table_name="civicvoice_analysis_records")
    op.drop_index("ix_civicvoice_analysis_records_category", table_name="civicvoice_analysis_records")
    op.drop_index("ix_civicvoice_analysis_records_source_record_id", table_name="civicvoice_analysis_records")
    op.drop_table("civicvoice_analysis_records")
