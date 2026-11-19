"""add google maps url and campaign advertisement image

Revision ID: t0u1v2w3x4y5
Revises: s9t0u1v2w3x4
Create Date: 2026-11-18 22:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "t0u1v2w3x4y5"
down_revision: str | None = "s9t0u1v2w3x4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Update nammadeals_business_registrations
    op.add_column(
        "nammadeals_business_registrations",
        sa.Column("google_maps_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "nammadeals_business_registrations",
        sa.Column("logo_url", sa.String(length=500), nullable=True),
    )

    # 2. Update nammadeals_businesses
    op.add_column(
        "nammadeals_businesses",
        sa.Column("google_maps_url", sa.Text(), nullable=True),
    )
    op.add_column(
        "nammadeals_businesses",
        sa.Column("logo_url", sa.String(length=500), nullable=True),
    )

    # 3. Update nammadeals_campaigns
    op.add_column(
        "nammadeals_campaigns",
        sa.Column("advertisement_image_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "nammadeals_campaigns",
        sa.Column("targeting_mode", sa.String(length=30), server_default="BOTH", nullable=False),
    )
    op.add_column(
        "nammadeals_campaigns",
        sa.Column("status", sa.String(length=30), server_default="ACTIVE", nullable=False),
    )
    op.create_index(
        "ix_nammadeals_campaigns_status",
        "nammadeals_campaigns",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index("ix_nammadeals_campaigns_status", table_name="nammadeals_campaigns")
    op.drop_column("nammadeals_campaigns", "status")
    op.drop_column("nammadeals_campaigns", "targeting_mode")
    op.drop_column("nammadeals_campaigns", "advertisement_image_url")
    op.drop_column("nammadeals_businesses", "logo_url")
    op.drop_column("nammadeals_businesses", "google_maps_url")
    op.drop_column("nammadeals_business_registrations", "logo_url")
    op.drop_column("nammadeals_business_registrations", "google_maps_url")
