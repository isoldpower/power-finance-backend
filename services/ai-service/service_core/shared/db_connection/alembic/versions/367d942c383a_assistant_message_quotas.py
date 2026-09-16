"""assistant message quotas

Revision ID: 367d942c383a
Revises: b5d1a90c74e3
Create Date: 2026-09-15 21:14:50.631801
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = '367d942c383a'
down_revision: str | None = 'b5d1a90c74e3'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('ai_assistant_quotas',
    sa.Column('external_id', sa.String(length=255), nullable=False),
    sa.Column('message_allowance', sa.Integer(), nullable=False),
    sa.Column('messages_consumed', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.PrimaryKeyConstraint('external_id')
    )


def downgrade() -> None:
    op.drop_table('ai_assistant_quotas')
