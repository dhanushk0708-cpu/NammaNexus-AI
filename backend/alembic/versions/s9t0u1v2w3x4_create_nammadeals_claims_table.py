"""create nammadeals coupon claims table

Revision ID: s9t0u1v2w3x4
Revises: r8s9t0u1v2w3
Create Date: 2026-11-18 22:00:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "s9t0u1v2w3x4"
down_revision: str | None = "r8s9t0u1v2w3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    json_col = postgresql.JSONB(astext_type=sa.Text()) if is_postgres else sa.JSON()

    op.create_table(
        "nammadeals_coupon_claims",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("citizen_user_id", sa.String(length=100), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=False),
        sa.Column("unique_coupon_code", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=30), server_default="CLAIMED", nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("redeemed_by_business_id", sa.String(length=36), nullable=True),
        sa.Column("redemption_notes", sa.Text(), nullable=True),
        sa.Column("scratch_reward_revealed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("claim_metadata", json_col, nullable=True),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["nammadeals_campaigns.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["nammadeals_offers.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["redeemed_by_business_id"],
            ["nammadeals_businesses.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("unique_coupon_code"),
        sa.UniqueConstraint("citizen_user_id", "offer_id", name="uq_nammadeals_citizen_offer_claim"),
    )
    op.create_index(
        "ix_nammadeals_coupon_claims_citizen_user_id",
        "nammadeals_coupon_claims",
        ["citizen_user_id"],
    )
    op.create_index(
        "ix_nammadeals_coupon_claims_campaign_id",
        "nammadeals_coupon_claims",
        ["campaign_id"],
    )
    op.create_index(
        "ix_nammadeals_coupon_claims_offer_id",
        "nammadeals_coupon_claims",
        ["offer_id"],
    )
    op.create_index(
        "ix_nammadeals_coupon_claims_unique_coupon_code",
        "nammadeals_coupon_claims",
        ["unique_coupon_code"],
    )
    op.create_index(
        "ix_nammadeals_coupon_claims_status",
        "nammadeals_coupon_claims",
        ["status"],
    )
    op.create_index(
        "ix_nammadeals_coupon_claims_redeemed_by_business_id",
        "nammadeals_coupon_claims",
        ["redeemed_by_business_id"],
    )


def downgrade() -> None:
    op.drop_table("nammadeals_coupon_claims")
