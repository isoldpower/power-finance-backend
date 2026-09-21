"""account currency and posting book values

Bookkeeping is always USD. Accounts say so explicitly, and every posting carries
what it is worth in the book alongside what the transaction actually said, with
the rate that got between them.

Backfilled, as `38b33afa2e50` did, with a server default that is then stripped:
the columns are NOT NULL, so postings written before booking existed need a
value the moment the column appears.

The backfill is deliberately `book_amount = amount` at `conversion_rate = 1`.
It is not a claim those postings were in USD — it is the only value that leaves
existing balances exactly where they already are, because they were computed
from `amount`. Any other rate would silently restate history against a number
nobody recorded at the time.

Revision ID: e52fe8499a10
Revises: 8ba9950c17a2
Create Date: 2026-08-31 07:44:11.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e52fe8499a10"
down_revision: str | None = "8ba9950c17a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "ai_accounts",
        sa.Column(
            "currency_code",
            sa.String(length=3),
            nullable=False,
            server_default=sa.text("'USD'"),
        ),
    )
    op.alter_column("ai_accounts", "currency_code", server_default=None)

    op.add_column(
        "ai_entries",
        sa.Column("book_amount", sa.Numeric(precision=20, scale=2), nullable=True),
    )
    op.add_column(
        "ai_entries",
        sa.Column(
            "book_currency",
            sa.String(length=3),
            nullable=False,
            server_default=sa.text("'USD'"),
        ),
    )
    op.add_column(
        "ai_entries",
        sa.Column(
            "conversion_rate",
            sa.Numeric(precision=24, scale=12),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )

    op.execute("UPDATE ai_entries SET book_amount = amount WHERE book_amount IS NULL")
    op.alter_column("ai_entries", "book_amount", nullable=False)

    op.alter_column("ai_entries", "book_currency", server_default=None)
    op.alter_column("ai_entries", "conversion_rate", server_default=None)


def downgrade() -> None:
    op.drop_column("ai_entries", "conversion_rate")
    op.drop_column("ai_entries", "book_currency")
    op.drop_column("ai_entries", "book_amount")
    op.drop_column("ai_accounts", "currency_code")
