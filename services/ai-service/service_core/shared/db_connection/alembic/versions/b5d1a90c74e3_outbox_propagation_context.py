"""outbox propagation context

Revision ID: b5d1a90c74e3
Revises: a1c7d4e90b32
Create Date: 2026-09-12 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = 'b5d1a90c74e3'
down_revision: str | None = 'a1c7d4e90b32'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('ai_outbox_events', sa.Column('traceparent', sa.String(length=64), nullable=True))
    op.add_column('ai_outbox_events', sa.Column('tracestate', sa.String(length=512), nullable=True))
    op.add_column('ai_outbox_events', sa.Column('baggage', sa.String(length=1024), nullable=True))


def downgrade() -> None:
    op.drop_column('ai_outbox_events', 'baggage')
    op.drop_column('ai_outbox_events', 'tracestate')
    op.drop_column('ai_outbox_events', 'traceparent')
