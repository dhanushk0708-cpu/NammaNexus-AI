"""create nammaserve tables

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-09-21 12:06:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h8i9j0k1l2m3"
down_revision: str | None = "g7h8i9j0k1l2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. service_categories
    op.create_table(
        "service_categories",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon_name", sa.String(length=50), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_service_categories_slug"), "service_categories", ["slug"], unique=True)

    # 2. providers
    op.create_table(
        "providers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("contact_person", sa.String(length=100), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("alternate_phone", sa.String(length=20), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("primary_area", sa.String(length=100), nullable=True),
        sa.Column("city", sa.String(length=50), nullable=False, server_default="Bengaluru"),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("service_radius_km", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("operating_hours", sa.String(length=100), nullable=True),
        sa.Column("is_emergency_service", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("verification_status", sa.String(length=30), nullable=False, server_default="UNVERIFIED"),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="LOCAL_DATABASE"),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_providers_name"), "providers", ["name"], unique=False)
    op.create_index(op.f("ix_providers_phone"), "providers", ["phone"], unique=False)
    op.create_index(op.f("ix_providers_primary_area"), "providers", ["primary_area"], unique=False)
    op.create_index(op.f("ix_providers_is_active"), "providers", ["is_active"], unique=False)
    op.create_index(op.f("ix_providers_verification_status"), "providers", ["verification_status"], unique=False)

    # 3. provider_services
    op.create_table(
        "provider_services",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("category_id", sa.String(length=36), nullable=False),
        sa.Column("price_min", sa.Float(), nullable=True),
        sa.Column("price_max", sa.Float(), nullable=True),
        sa.Column("price_unit", sa.String(length=50), nullable=True),
        sa.Column("minimum_order", sa.String(length=100), nullable=True),
        sa.Column("capacity", sa.String(length=100), nullable=True),
        sa.Column("water_type", sa.String(length=50), nullable=True),
        sa.Column("availability", sa.String(length=100), nullable=True),
        sa.Column("payment_methods", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("verification_status", sa.String(length=30), nullable=False, server_default="UNVERIFIED"),
        sa.Column("source", sa.String(length=255), nullable=True),
        sa.Column("source_type", sa.String(length=50), nullable=False, server_default="LOCAL_DATABASE"),
        sa.Column("source_url", sa.String(length=500), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["service_categories.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "category_id", name="uq_provider_category"),
    )
    op.create_index(op.f("ix_provider_services_provider_id"), "provider_services", ["provider_id"], unique=False)
    op.create_index(op.f("ix_provider_services_category_id"), "provider_services", ["category_id"], unique=False)
    op.create_index(op.f("ix_provider_services_verification_status"), "provider_services", ["verification_status"], unique=False)

    # 4. provider_service_areas
    op.create_table(
        "provider_service_areas",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("provider_id", sa.String(length=36), nullable=False),
        sa.Column("area_name", sa.String(length=100), nullable=False),
        sa.Column("ward_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["provider_id"], ["providers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_id", "area_name", name="uq_provider_area"),
    )
    op.create_index(op.f("ix_provider_service_areas_provider_id"), "provider_service_areas", ["provider_id"], unique=False)
    op.create_index(op.f("ix_provider_service_areas_area_name"), "provider_service_areas", ["area_name"], unique=False)


def downgrade() -> None:
    op.drop_table("provider_service_areas")
    op.drop_table("provider_services")
    op.drop_table("providers")
    op.drop_table("service_categories")
