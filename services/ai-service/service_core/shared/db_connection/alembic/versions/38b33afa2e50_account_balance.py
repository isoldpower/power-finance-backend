"""account balance

Added with a server default and then stripped of it: the column is NOT NULL, so
existing accounts need a value at the moment it appears, but the model does not
declare a database-side default and leaving one behind would make the next
autogenerate want to remove it.

Revision ID: 38b33afa2e50
Revises: 978c45f7e58a
Create Date: 2026-08-25 22:22:12.211380
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "38b33afa2e50"
down_revision: str | None = "978c45f7e58a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_accounts",
        sa.Column(
            "balance",
            sa.Numeric(precision=20, scale=2),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.alter_column("ai_accounts", "balance", server_default=None)


def downgrade() -> None:
    op.drop_column("ai_accounts", "balance")
