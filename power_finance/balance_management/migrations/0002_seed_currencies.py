from django.db import migrations
import json
from pathlib import Path


def seed_currencies(apps, schema_editor):
    currency = apps.get_model("balance_management", "Currency")

    file_path = Path(__file__).resolve().parent.parent / "data" / "currencies.json"

    with open(file_path) as f:
        data = json.load(f)

    currency.objects.bulk_create(
        [
            currency(
                code=c["code"],
                name=c["currency"],
                numeric=c["number"],
                digits=c["digits"],
            )
            for c in data
        ],
        ignore_conflicts=True,
    )


class Migration(migrations.Migration):

    dependencies = [
        ("balance_management", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_currencies, migrations.RunPython.noop),
    ]
