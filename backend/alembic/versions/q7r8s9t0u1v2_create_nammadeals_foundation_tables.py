"""create nammadeals foundation tables

Revision ID: q7r8s9t0u1v2
Revises: p6q7r8s9t0u1
Create Date: 2026-11-18 21:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "q7r8s9t0u1v2"
down_revision: str | None = "p6q7r8s9t0u1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    json_col = postgresql.JSONB(astext_type=sa.Text()) if is_postgres else sa.JSON()

    # 1. Business Registrations
    op.create_table(
        "nammadeals_business_registrations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("business_name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("contact_name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("city", sa.String(length=100), server_default="Bengaluru", nullable=False),
        sa.Column("area", sa.String(length=100), nullable=False),
        sa.Column("pincode", sa.String(length=10), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="PENDING", nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=100), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_nammadeals_business_registrations_category",
        "nammadeals_business_registrations",
        ["category"],
    )
    op.create_index(
        "ix_nammadeals_business_registrations_email",
        "nammadeals_business_registrations",
        ["email"],
    )
    op.create_index(
        "ix_nammadeals_business_registrations_area",
        "nammadeals_business_registrations",
        ["area"],
    )
    op.create_index(
        "ix_nammadeals_business_registrations_pincode",
        "nammadeals_business_registrations",
        ["pincode"],
    )
    op.create_index(
        "ix_nammadeals_business_registrations_status",
        "nammadeals_business_registrations",
        ["status"],
    )

    # 2. Businesses
    op.create_table(
        "nammadeals_businesses",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_user_id", sa.String(length=100), nullable=False),
        sa.Column("registration_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("address", sa.Text(), nullable=False),
        sa.Column("city", sa.String(length=100), server_default="Bengaluru", nullable=False),
        sa.Column("area", sa.String(length=100), nullable=False),
        sa.Column("pincode", sa.String(length=10), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="PENDING", nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("verified_by", sa.String(length=100), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["registration_id"],
            ["nammadeals_business_registrations.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("registration_id"),
    )
    op.create_index(
        "ix_nammadeals_businesses_owner_user_id",
        "nammadeals_businesses",
        ["owner_user_id"],
    )
    op.create_index(
        "ix_nammadeals_businesses_category",
        "nammadeals_businesses",
        ["category"],
    )
    op.create_index(
        "ix_nammadeals_businesses_area",
        "nammadeals_businesses",
        ["area"],
    )
    op.create_index(
        "ix_nammadeals_businesses_pincode",
        "nammadeals_businesses",
        ["pincode"],
    )
    op.create_index(
        "ix_nammadeals_businesses_status",
        "nammadeals_businesses",
        ["status"],
    )

    # 3. Campaigns
    op.create_table(
        "nammadeals_campaigns",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("business_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("campaign_type", sa.String(length=50), server_default="DISCOUNT", nullable=False),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("approval_status", sa.String(length=30), server_default="DRAFT", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("targeting_strategy", sa.String(length=50), server_default="RADIUS", nullable=False),
        sa.Column("targeting_radius_km", sa.Float(), server_default="5.0", nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("priority", sa.Integer(), server_default="10", nullable=False),
        sa.Column("frequency_limit_per_user", sa.Integer(), server_default="3", nullable=False),
        sa.Column("placement_config", json_col, nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.String(length=100), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["nammadeals_businesses.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_nammadeals_campaigns_business_id",
        "nammadeals_campaigns",
        ["business_id"],
    )
    op.create_index(
        "ix_nammadeals_campaigns_approval_status",
        "nammadeals_campaigns",
        ["approval_status"],
    )
    op.create_index(
        "ix_nammadeals_campaigns_is_active",
        "nammadeals_campaigns",
        ["is_active"],
    )

    # 4. Offers
    op.create_table(
        "nammadeals_offers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("promotional_image_url", sa.String(length=500), nullable=True),
        sa.Column("discount_type", sa.String(length=30), server_default="PERCENTAGE", nullable=False),
        sa.Column("discount_value", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("terms_and_conditions", sa.Text(), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_until", sa.DateTime(timezone=True), nullable=False),
        sa.Column("offer_type", sa.String(length=30), server_default="COUPON", nullable=False),
        sa.Column("coupon_code", sa.String(length=50), nullable=True),
        sa.Column("scratch_card_config", json_col, nullable=True),
        sa.Column("max_redemptions", sa.Integer(), server_default="100", nullable=False),
        sa.Column("redemption_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["nammadeals_campaigns.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_nammadeals_offers_campaign_id",
        "nammadeals_offers",
        ["campaign_id"],
    )
    op.create_index(
        "ix_nammadeals_offers_coupon_code",
        "nammadeals_offers",
        ["coupon_code"],
    )
    op.create_index(
        "ix_nammadeals_offers_is_active",
        "nammadeals_offers",
        ["is_active"],
    )

    # 5. Advertiser Payments
    op.create_table(
        "nammadeals_payments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("business_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False),
        sa.Column("currency", sa.String(length=10), server_default="INR", nullable=False),
        sa.Column("transaction_id", sa.String(length=100), nullable=False),
        sa.Column("payment_method", sa.String(length=50), server_default="UPI", nullable=False),
        sa.Column("payment_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verification_status", sa.String(length=30), server_default="PENDING", nullable=False),
        sa.Column("admin_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["business_id"],
            ["nammadeals_businesses.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["nammadeals_campaigns.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transaction_id"),
    )
    op.create_index(
        "ix_nammadeals_payments_business_id",
        "nammadeals_payments",
        ["business_id"],
    )
    op.create_index(
        "ix_nammadeals_payments_campaign_id",
        "nammadeals_payments",
        ["campaign_id"],
    )
    op.create_index(
        "ix_nammadeals_payments_transaction_id",
        "nammadeals_payments",
        ["transaction_id"],
    )
    op.create_index(
        "ix_nammadeals_payments_verification_status",
        "nammadeals_payments",
        ["verification_status"],
    )


def downgrade() -> None:
    op.drop_table("nammadeals_payments")
    op.drop_table("nammadeals_offers")
    op.drop_table("nammadeals_campaigns")
    op.drop_table("nammadeals_businesses")
    op.drop_table("nammadeals_business_registrations")
