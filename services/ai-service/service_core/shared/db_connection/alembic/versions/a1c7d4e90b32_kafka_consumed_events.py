"""kafka consumed events

Revision ID: a1c7d4e90b32
Revises: 3241f96ca480
Create Date: 2026-09-08 01:10:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = 'a1c7d4e90b32'
down_revision: str | None = '3241f96ca480'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('kafka_consumed_events',
    sa.Column('consumer_group', sa.Text(), nullable=False),
    sa.Column('event_id', sa.Text(), nullable=False),
    sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('consumer_group', 'event_id')
    )
    op.create_index('kafka_consumed_events_consumed_at_idx', 'kafka_consumed_events', ['consumed_at'], unique=False)


def downgrade() -> None:
    op.drop_index('kafka_consumed_events_consumed_at_idx', table_name='kafka_consumed_events')
    op.drop_table('kafka_consumed_events')
