"""users and outbox

Two tables that exist so this service can publish: `ai_users` holds the external
id every event is keyed by, and `ai_outbox_events` is the outbox Debezium tails.
The outbox column names are the Event Router SMT's defaults, not this schema's
taste.

Revision ID: 87a508cf0bf2
Revises: 38b33afa2e50
Create Date: 2026-08-27 22:18:51.300903
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "87a508cf0bf2"
down_revision: str | None = "38b33afa2e50"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_users",
        sa.Column("user_id", sa.Integer(), autoincrement=False, nullable=False),
        sa.Column("external_id", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("external_id"),
    )
    op.create_table(
        "ai_outbox_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("aggregatetype", sa.String(length=64), nullable=False),
        sa.Column("aggregateid", sa.String(length=64), nullable=False),
        sa.Column("partitionkey", sa.String(length=255), nullable=False),
        sa.Column("type", sa.String(length=128), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id"),
    )
    op.create_index(
        "ai_outbox_events_aggregate",
        "ai_outbox_events",
        ["aggregatetype", "aggregateid"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ai_outbox_events_aggregate", table_name="ai_outbox_events")
    op.drop_table("ai_outbox_events")
    op.drop_table("ai_users")
