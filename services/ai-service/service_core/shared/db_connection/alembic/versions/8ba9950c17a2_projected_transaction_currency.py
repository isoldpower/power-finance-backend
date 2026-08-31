"""projected transaction currency

Added with a server default and then stripped of it, as `38b33afa2e50` did: the
column is NOT NULL, so transactions projected before it existed need a value at
the moment it appears, and leaving the default behind would make the next
autogenerate want to remove it.

Those older rows keep the empty string. The currency they were created under is
not recoverable here — ai-service never projected it — so an empty code means
"unknown", which is what the dispatcher writes through as a NULL posting
currency rather than inventing one.

Revision ID: 8ba9950c17a2
Revises: 87a508cf0bf2
Create Date: 2026-08-30 19:34:22.687049
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "8ba9950c17a2"
down_revision: str | None = "87a508cf0bf2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_projected_transactions",
        sa.Column(
            "currency_code",
            sa.String(length=3),
            nullable=False,
            server_default=sa.text("''"),
        ),
    )
    op.alter_column("ai_projected_transactions", "currency_code", server_default=None)


def downgrade() -> None:
    op.drop_column("ai_projected_transactions", "currency_code")
