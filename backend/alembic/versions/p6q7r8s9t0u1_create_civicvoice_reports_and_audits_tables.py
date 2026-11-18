"""create civicvoice reports and report audits tables

Revision ID: p6q7r8s9t0u1
Revises: o5p6q7r8s9t0
Create Date: 2026-10-29 23:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "p6q7r8s9t0u1"
down_revision: str | None = "o5p6q7r8s9t0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    json_col = postgresql.JSONB(astext_type=sa.Text()) if is_postgres else sa.JSON()

    op.create_table(
        "civicvoice_reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("geographic_scope", sa.String(length=150), server_default="Bengaluru Urban (BBMP Wards)", nullable=False),
        sa.Column("reporting_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reporting_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="draft", nullable=False),
        sa.Column("authority_name", sa.String(length=200), nullable=False),
        sa.Column("department_name", sa.String(length=200), nullable=False),
        sa.Column("recipient_email", sa.String(length=255), nullable=True),
        sa.Column("official_portal_url", sa.String(length=500), nullable=True),
        sa.Column("mapping_verified", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("mapping_source_url", sa.String(length=500), nullable=True),
        sa.Column("mapping_last_verified", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_records_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("citizen_submissions_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("summary_content", sa.Text(), nullable=False),
        sa.Column("recommendations", sa.Text(), nullable=False),
        sa.Column("themes_summary", json_col, nullable=True),
        sa.Column("sentiment_summary", json_col, nullable=True),
        sa.Column("evidence_urls", json_col, nullable=True),
        sa.Column("limitations", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("approved_by", sa.String(length=100), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("idempotency_key", sa.String(length=64), nullable=True),
        sa.Column("delivery_details", json_col, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_civicvoice_reports_topic", "civicvoice_reports", ["topic"], unique=False)
    op.create_index("ix_civicvoice_reports_status", "civicvoice_reports", ["status"], unique=False)
    op.create_index("ix_civicvoice_reports_idempotency_key", "civicvoice_reports", ["idempotency_key"], unique=False)

    op.create_table(
        "civicvoice_report_audits",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("report_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("performed_by", sa.String(length=100), nullable=False),
        sa.Column("previous_status", sa.String(length=30), nullable=True),
        sa.Column("new_status", sa.String(length=30), nullable=True),
        sa.Column("details_json", json_col, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["report_id"], ["civicvoice_reports.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_civicvoice_report_audits_report_id", "civicvoice_report_audits", ["report_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_civicvoice_report_audits_report_id", table_name="civicvoice_report_audits")
    op.drop_table("civicvoice_report_audits")

    op.drop_index("ix_civicvoice_reports_idempotency_key", table_name="civicvoice_reports")
    op.drop_index("ix_civicvoice_reports_status", table_name="civicvoice_reports")
    op.drop_index("ix_civicvoice_reports_topic", table_name="civicvoice_reports")
    op.drop_table("civicvoice_reports")
