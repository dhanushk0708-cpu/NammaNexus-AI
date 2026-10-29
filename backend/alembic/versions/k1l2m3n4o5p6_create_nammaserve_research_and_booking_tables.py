"""create nammaserve research candidates, coverage, and booking tables

Revision ID: k1l2m3n4o5p6
Revises: j0k1l2m3n4
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "k1l2m3n4o5p6"
down_revision: str | None = "j0k1l2m3n4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. nammaserve_research_candidates table
    op.create_table(
        "nammaserve_research_candidates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("batch_id", sa.String(length=20), nullable=False),
        sa.Column("provider_id", sa.String(length=50), nullable=False),
        sa.Column("provider_name", sa.String(length=200), nullable=False),
        sa.Column("service_category", sa.String(length=100), nullable=False),
        sa.Column("raw_service_category", sa.String(length=150), nullable=False),
        sa.Column("specific_services", sa.Text(), nullable=True),
        sa.Column("requested_area", sa.String(length=100), nullable=False),
        sa.Column("area_name", sa.String(length=50), nullable=False),
        sa.Column("business_address", sa.Text(), nullable=True),
        sa.Column("public_phone", sa.String(length=100), nullable=True),
        sa.Column("public_email", sa.String(length=150), nullable=True),
        sa.Column("website_url", sa.String(length=500), nullable=True),
        sa.Column("contact_or_booking_url", sa.String(length=500), nullable=True),
        sa.Column("advertised_service_areas", sa.Text(), nullable=True),
        sa.Column("area_coverage_evidence_url", sa.String(length=500), nullable=True),
        sa.Column("price_type", sa.String(length=50), nullable=True),
        sa.Column("price_amount", sa.Float(), nullable=True),
        sa.Column("price_currency", sa.String(length=10), server_default="INR", nullable=False),
        sa.Column("price_unit", sa.String(length=100), nullable=True),
        sa.Column("price_scope", sa.Text(), nullable=True),
        sa.Column("price_source_url", sa.String(length=500), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("review_count", sa.Integer(), nullable=True),
        sa.Column("rating_platform", sa.String(length=100), nullable=True),
        sa.Column("rating_source_url", sa.String(length=500), nullable=True),
        sa.Column("booking_method", sa.Text(), nullable=True),
        sa.Column("availability_status", sa.String(length=50), server_default="UNKNOWN", nullable=False),
        sa.Column("verification_status", sa.String(length=50), server_default="DISCOVERED", nullable=False),
        sa.Column("primary_source_url", sa.String(length=500), nullable=True),
        sa.Column("secondary_source_url", sa.String(length=500), nullable=True),
        sa.Column("research_date", sa.String(length=20), nullable=True),
        sa.Column("confidence", sa.String(length=20), server_default="HIGH", nullable=False),
        sa.Column("evidence_summary", sa.Text(), nullable=True),
        sa.Column("missing_information", sa.Text(), nullable=True),
        sa.Column("duplicate_group_id", sa.String(length=50), nullable=True),
        sa.Column("provider_rank", sa.Integer(), server_default="1", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("review_summary", sa.Text(), nullable=True),
        sa.Column("review_positive_themes", sa.Text(), nullable=True),
        sa.Column("review_negative_themes", sa.Text(), nullable=True),
        sa.Column("review_date_range", sa.String(length=100), nullable=True),
        sa.Column("review_summary_source_url", sa.String(length=500), nullable=True),
        sa.Column("review_summary_limitations", sa.Text(), nullable=True),
        sa.Column("raw_record", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_name", "requested_area", "service_category", name="uq_research_candidate_prov_area_cat"),
    )
    op.create_index("ix_research_candidates_batch_id", "nammaserve_research_candidates", ["batch_id"], unique=False)
    op.create_index("ix_research_candidates_provider_id", "nammaserve_research_candidates", ["provider_id"], unique=False)
    op.create_index("ix_research_candidates_provider_name", "nammaserve_research_candidates", ["provider_name"], unique=False)
    op.create_index("ix_research_candidates_service_category", "nammaserve_research_candidates", ["service_category"], unique=False)
    op.create_index("ix_research_candidates_requested_area", "nammaserve_research_candidates", ["requested_area"], unique=False)
    op.create_index("ix_research_candidates_area_name", "nammaserve_research_candidates", ["area_name"], unique=False)
    op.create_index("ix_research_candidates_verification_status", "nammaserve_research_candidates", ["verification_status"], unique=False)
    op.create_index("ix_research_candidates_price_type", "nammaserve_research_candidates", ["price_type"], unique=False)
    op.create_index("ix_research_candidates_duplicate_group_id", "nammaserve_research_candidates", ["duplicate_group_id"], unique=False)

    # 2. nammaserve_research_coverage table
    op.create_table(
        "nammaserve_research_coverage",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("batch_id", sa.String(length=20), nullable=False),
        sa.Column("area", sa.String(length=100), nullable=False),
        sa.Column("clean_area", sa.String(length=50), nullable=False),
        sa.Column("service_category", sa.String(length=100), nullable=False),
        sa.Column("research_status", sa.String(length=50), server_default="COMPLETED_WITH_RESULTS", nullable=False),
        sa.Column("provider_1_id", sa.String(length=50), nullable=True),
        sa.Column("provider_1_name", sa.String(length=200), nullable=True),
        sa.Column("provider_1_source_url", sa.String(length=500), nullable=True),
        sa.Column("provider_2_id", sa.String(length=50), nullable=True),
        sa.Column("provider_2_name", sa.String(length=200), nullable=True),
        sa.Column("provider_2_source_url", sa.String(length=500), nullable=True),
        sa.Column("providers_found", sa.Integer(), server_default="2", nullable=False),
        sa.Column("sources_checked", sa.Text(), nullable=True),
        sa.Column("evidence_summary", sa.Text(), nullable=True),
        sa.Column("limitations", sa.Text(), nullable=True),
        sa.Column("research_date", sa.String(length=20), nullable=True),
        sa.Column("raw_record", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("area", "service_category", name="uq_research_coverage_area_cat"),
    )
    op.create_index("ix_research_coverage_batch_id", "nammaserve_research_coverage", ["batch_id"], unique=False)
    op.create_index("ix_research_coverage_area", "nammaserve_research_coverage", ["area"], unique=False)
    op.create_index("ix_research_coverage_clean_area", "nammaserve_research_coverage", ["clean_area"], unique=False)
    op.create_index("ix_research_coverage_service_category", "nammaserve_research_coverage", ["service_category"], unique=False)

    # 3. nammaserve_booking_requests table
    op.create_table(
        "nammaserve_booking_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=True),
        sa.Column("provider_name", sa.String(length=200), nullable=False),
        sa.Column("service_category", sa.String(length=100), nullable=False),
        sa.Column("area", sa.String(length=100), nullable=False),
        sa.Column("customer_name", sa.String(length=100), nullable=False),
        sa.Column("customer_phone", sa.String(length=50), nullable=False),
        sa.Column("customer_email", sa.String(length=150), nullable=True),
        sa.Column("customer_address", sa.Text(), nullable=True),
        sa.Column("preferred_date", sa.String(length=50), nullable=True),
        sa.Column("preferred_time_slot", sa.String(length=50), nullable=True),
        sa.Column("issue_description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), server_default="PENDING_CONFIRMATION", nullable=False),
        sa.Column("is_research_candidate", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["nammaserve_research_candidates.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_booking_requests_candidate_id", "nammaserve_booking_requests", ["candidate_id"], unique=False)
    op.create_index("ix_booking_requests_status", "nammaserve_booking_requests", ["status"], unique=False)


def downgrade() -> None:
    op.drop_table("nammaserve_booking_requests")
    op.drop_table("nammaserve_research_coverage")
    op.drop_table("nammaserve_research_candidates")
