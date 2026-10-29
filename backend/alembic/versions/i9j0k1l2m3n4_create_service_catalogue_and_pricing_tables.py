"""create service catalogue and pricing tables

Revision ID: i9j0k1l2m3n4
Revises: h8i9j0k1l2m3
Create Date: 2026-10-22 00:25:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i9j0k1l2m3n4"
down_revision: str | None = "h8i9j0k1l2m3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. services (Individual catalogue services under categories)
    op.create_table(
        "services",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("category_id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["service_categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_services_slug"), "services", ["slug"], unique=True)
    op.create_index(op.f("ix_services_category_id"), "services", ["category_id"], unique=False)
    op.create_index(op.f("ix_services_name"), "services", ["name"], unique=False)
    op.create_index(op.f("ix_services_is_active"), "services", ["is_active"], unique=False)

    # 2. platform_listings (Urban Company, NoBroker, Justdial, Sulekha, Direct Local)
    op.create_table(
        "platform_listings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("service_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("locality", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=50), nullable=False, server_default="Bengaluru"),
        sa.Column("listing_url", sa.String(length=500), nullable=True),
        sa.Column("booking_url", sa.String(length=500), nullable=True),
        sa.Column("verification_status", sa.String(length=30), nullable=False, server_default="UNVERIFIED"),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_platform_listings_platform"), "platform_listings", ["platform"], unique=False)
    op.create_index(op.f("ix_platform_listings_service_id"), "platform_listings", ["service_id"], unique=False)
    op.create_index(op.f("ix_platform_listings_locality"), "platform_listings", ["locality"], unique=False)
    op.create_index(op.f("ix_platform_listings_verification_status"), "platform_listings", ["verification_status"], unique=False)
    op.create_index(op.f("ix_platform_listings_is_active"), "platform_listings", ["is_active"], unique=False)

    # 3. provider_offerings (Evolving provider-service relationships to individual services)
    op.create_table(
        "provider_offerings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("service_id", sa.String(length=36), nullable=False),
        sa.Column("custom_name", sa.String(length=150), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("verification_status", sa.String(length=30), nullable=False, server_default="UNVERIFIED"),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "service_id", name="uq_provider_individual_service"),
    )
    op.create_index(op.f("ix_provider_offerings_provider_id"), "provider_offerings", ["provider_id"], unique=False)
    op.create_index(op.f("ix_provider_offerings_service_id"), "provider_offerings", ["service_id"], unique=False)
    op.create_index(op.f("ix_provider_offerings_is_active"), "provider_offerings", ["is_active"], unique=False)
    op.create_index(op.f("ix_provider_offerings_verification_status"), "provider_offerings", ["verification_status"], unique=False)

    # 4. service_prices (Supporting FIXED, STARTING_AT, RANGE, QUOTE_REQUIRED, CONSULTATION_FEE, PER_UNIT)
    op.create_table(
        "service_prices",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("service_id", sa.String(length=36), nullable=False),
        sa.Column("price_type", sa.String(length=30), nullable=False),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("price_min", sa.Float(), nullable=True),
        sa.Column("price_max", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="INR"),
        sa.Column("unit", sa.String(length=50), nullable=True),
        sa.Column("platform_listing_id", sa.String(length=36), nullable=True),
        sa.Column("provider_offering_id", sa.String(length=36), nullable=True),
        sa.Column("conditions", sa.Text(), nullable=True),
        sa.Column("inclusions", sa.Text(), nullable=True),
        sa.Column("exclusions", sa.Text(), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("verification_status", sa.String(length=30), nullable=False, server_default="UNVERIFIED"),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["platform_listing_id"], ["platform_listings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["provider_offering_id"], ["provider_offerings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_service_prices_service_id"), "service_prices", ["service_id"], unique=False)
    op.create_index(op.f("ix_service_prices_price_type"), "service_prices", ["price_type"], unique=False)
    op.create_index(op.f("ix_service_prices_platform_listing_id"), "service_prices", ["platform_listing_id"], unique=False)
    op.create_index(op.f("ix_service_prices_provider_offering_id"), "service_prices", ["provider_offering_id"], unique=False)
    op.create_index(op.f("ix_service_prices_verification_status"), "service_prices", ["verification_status"], unique=False)

    # 5. citizen_reviews (Citizen-submitted authentic feedback)
    op.create_table(
        "citizen_reviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("service_id", sa.String(length=36), nullable=True),
        sa.Column("citizen_user_id", sa.String(length=100), nullable=True),
        sa.Column("rating", sa.Float(), nullable=False),
        sa.Column("review_title", sa.String(length=150), nullable=True),
        sa.Column("review_text", sa.Text(), nullable=False),
        sa.Column("locality", sa.String(length=100), nullable=True),
        sa.Column("service_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_verified_resident", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_citizen_reviews_provider_id"), "citizen_reviews", ["provider_id"], unique=False)
    op.create_index(op.f("ix_citizen_reviews_service_id"), "citizen_reviews", ["service_id"], unique=False)
    op.create_index(op.f("ix_citizen_reviews_citizen_user_id"), "citizen_reviews", ["citizen_user_id"], unique=False)
    op.create_index(op.f("ix_citizen_reviews_locality"), "citizen_reviews", ["locality"], unique=False)
    op.create_index(op.f("ix_citizen_reviews_is_published"), "citizen_reviews", ["is_published"], unique=False)

    # 6. third_party_reviews (Aggregated ratings strictly separated from citizen feedback)
    op.create_table(
        "third_party_reviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_id", sa.String(length=36), nullable=True),
        sa.Column("platform_listing_id", sa.String(length=36), nullable=True),
        sa.Column("source_platform", sa.String(length=50), nullable=False),
        sa.Column("external_rating", sa.Float(), nullable=True),
        sa.Column("external_reviews_count", sa.Integer(), nullable=True),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["platform_listing_id"], ["platform_listings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_third_party_reviews_provider_id"), "third_party_reviews", ["provider_id"], unique=False)
    op.create_index(op.f("ix_third_party_reviews_platform_listing_id"), "third_party_reviews", ["platform_listing_id"], unique=False)
    op.create_index(op.f("ix_third_party_reviews_source_platform"), "third_party_reviews", ["source_platform"], unique=False)


def downgrade() -> None:
    op.drop_table("third_party_reviews")
    op.drop_table("citizen_reviews")
    op.drop_table("service_prices")
    op.drop_table("provider_offerings")
    op.drop_table("platform_listings")
    op.drop_table("services")
