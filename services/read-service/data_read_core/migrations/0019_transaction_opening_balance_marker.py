from django.db import migrations, models

MARK_OPENING_BALANCES = """
UPDATE read_transactions AS transaction_row
SET is_opening_balance = TRUE
FROM read_wallets AS wallet_row
WHERE transaction_row.wallet_id = wallet_row.id
  AND transaction_row.container_kind = 'wallet'
  AND transaction_row.chain_id IS NULL
  AND transaction_row.created_at = wallet_row.created_at
"""


class Migration(migrations.Migration):
    dependencies = [
        ("data_read_core", "0018_espendingoutboxseq"),
    ]

    operations = [
        migrations.AddField(
            model_name="transactionreadmodel",
            name="is_opening_balance",
            field=models.BooleanField(default=False),
        ),
        migrations.RunSQL(MARK_OPENING_BALANCES, reverse_sql=migrations.RunSQL.noop),
    ]
