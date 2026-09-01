"""Denominate the chart of accounts, and order it the way the API says.

Two changes that have to travel together, because both touch the same indexes:

- `currency_code` carries the BOOK currency an account's balance is summed in.
  ai-service converts every posting into it before adding it up, so it is one
  value per account and not a property of the individual legs. Rows written
  before the producer emitted it are backfilled to `USD`, which is what
  `BOOK_CURRENCY` has been since the dispatcher was built;
- the chart's order becomes `created_at DESC, id DESC` — every collection in
  this API sorts that way, and `group` was never meant to. `ra_user_chart_idx`
  is rebuilt to serve the `group` FILTER and the `meta.groups` aggregate
  instead, and `ra_user_keyset_idx` takes over the sort.
"""

from django.db import migrations, models

BOOK_CURRENCY = "USD"


def fill_book_currency(apps, schema_editor):
    AccountReadModel = apps.get_model("data_read_core", "AccountReadModel")
    AccountReadModel.objects.filter(currency_code="").update(currency_code=BOOK_CURRENCY)


def clear_book_currency(apps, schema_editor):
    AccountReadModel = apps.get_model("data_read_core", "AccountReadModel")
    AccountReadModel.objects.update(currency_code="")


class Migration(migrations.Migration):
    dependencies = [
        ("data_read_core", "0012_accountdispatchreadmodel_accountpostingreadmodel_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="accountreadmodel",
            name="currency_code",
            field=models.CharField(blank=True, default="", max_length=8),
        ),
        migrations.RunPython(fill_book_currency, clear_book_currency),
        migrations.RemoveIndex(
            model_name="accountreadmodel",
            name="ra_user_chart_idx",
        ),
        migrations.AddIndex(
            model_name="accountreadmodel",
            index=models.Index(
                fields=["user_id", "-created_at", "-id"],
                include=("group", "name", "balance", "currency_code"),
                name="ra_user_keyset_idx",
            ),
        ),
        migrations.AddIndex(
            model_name="accountreadmodel",
            index=models.Index(
                fields=["user_id", "group"],
                include=("balance", "currency_code"),
                name="ra_user_chart_idx",
            ),
        ),
    ]
