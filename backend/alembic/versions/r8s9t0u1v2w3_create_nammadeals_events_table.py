"""create nammadeals events table

Revision ID: r8s9t0u1v2w3
Revises: q7r8s9t0u1v2
Create Date: 2026-11-18 21:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "r8s9t0u1v2w3"
down_revision: str | None = "q7r8s9t0u1v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"
    json_col = postgresql.JSONB(astext_type=sa.Text()) if is_postgres else sa.JSON()

    op.create_table(
        "nammadeals_promotion_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=False),
        sa.Column("offer_id", sa.String(length=36), nullable=True),
        sa.Column("citizen_user_id", sa.String(length=100), nullable=False),
        sa.Column("location_source", sa.String(length=30), nullable=True),
        sa.Column("idempotency_key", sa.String(length=100), nullable=True),
        sa.Column("event_metadata", json_col, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["nammadeals_campaigns.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["offer_id"],
            ["nammadeals_offers.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_nammadeals_promotion_events_event_type",
        "nammadeals_promotion_events",
        ["event_type"],
    )
    op.create_index(
        "ix_nammadeals_promotion_events_campaign_id",
        "nammadeals_promotion_events",
        ["campaign_id"],
    )
    op.create_index(
        "ix_nammadeals_promotion_events_offer_id",
        "nammadeals_promotion_events",
        ["offer_id"],
    )
    op.create_index(
        "ix_nammadeals_promotion_events_citizen_user_id",
        "nammadeals_promotion_events",
        ["citizen_user_id"],
    )
    op.create_index(
        "ix_nammadeals_promotion_events_idempotency_key",
        "nammadeals_promotion_events",
        ["idempotency_key"],
    )
    op.create_index(
        "ix_nammadeals_promotion_events_created_at",
        "nammadeals_promotion_events",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_table("nammadeals_promotion_events")
