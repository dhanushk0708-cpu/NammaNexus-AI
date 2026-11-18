"""create civicvoice citizen submissions table

Revision ID: n4o5p6q7r8s9
Revises: m3n4o5p6q7r8
Create Date: 2026-10-29
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "n4o5p6q7r8s9"
down_revision: str | None = "m3n4o5p6q7r8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "civicvoice_citizen_submissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("opinion_text", sa.Text(), nullable=False),
        sa.Column("locality", sa.String(length=100), nullable=True),
        sa.Column("language", sa.String(length=10), nullable=True, server_default="en"),
        sa.Column("consent_given", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_civicvoice_citizen_submissions_topic",
        "civicvoice_citizen_submissions",
        ["topic"],
        unique=False,
    )
    op.create_index(
        "ix_civicvoice_citizen_submissions_locality",
        "civicvoice_citizen_submissions",
        ["locality"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_civicvoice_citizen_submissions_locality",
        table_name="civicvoice_citizen_submissions",
    )
    op.drop_index(
        "ix_civicvoice_citizen_submissions_topic",
        table_name="civicvoice_citizen_submissions",
    )
    op.drop_table("civicvoice_citizen_submissions")
