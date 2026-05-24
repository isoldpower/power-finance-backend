"""Rebuild `outbox_events` with a BIGSERIAL primary key.

The original schema used a UUID PK which is fine as a row identifier but
unsuitable as a monotonic version token for read-your-writes. Read Service
needs to compare `Read-At-Least` headers against the latest applied write
version with `>=`; UUIDs do not order.

Migration is destructive — the table is dropped and rebuilt. This is safe
in dev because the outbox is processed by Debezium on the way out and never
read back by the service. In a production rollout the conversion would need
to be a multi-step online migration (add `seq` column, backfill, swap PK).

The stable per-event UUID lives on as `event_id` (unique, default uuid4)
so downstream consumers keep their idempotency key."""

import uuid

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("data_write_core", "0002_seed_currencies"),
    ]

    operations = [
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS outbox_events CASCADE",
            reverse_sql=migrations.RunSQL.noop,
            state_operations=[
                migrations.DeleteModel(name="OutboxEntryModel"),
            ],
        ),
        migrations.CreateModel(
            name="OutboxEntryModel",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                (
                    "event_id",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                (
                    "aggregate_type",
                    models.CharField(db_column="aggregatetype", max_length=64),
                ),
                (
                    "aggregate_id",
                    models.CharField(db_column="aggregateid", max_length=64),
                ),
                ("event_type", models.CharField(db_column="type", max_length=128)),
                ("payload", models.JSONField()),
                ("occurred_at", models.DateTimeField(default=django.utils.timezone.now)),
            ],
            options={
                "db_table": "outbox_events",
                "indexes": [
                    models.Index(
                        fields=["aggregate_type", "aggregate_id"],
                        name="outbox_even_aggrega_374270_idx",
                    )
                ],
            },
        ),
    ]
