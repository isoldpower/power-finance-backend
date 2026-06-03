from uuid import uuid4

from django.db import models
from django.utils import timezone


class OutboxEntryModel(models.Model):
    """Transactional outbox row. Written in the same DB transaction as
    business state. Debezium tails the Postgres WAL and forwards rows to
    Kafka via the Outbox Event Router SMT, so column names match the SMT's
    expected defaults (`aggregatetype`, `aggregateid`, `type`, `payload`)."""

    id = models.BigAutoField(primary_key=True)
    event_id = models.UUIDField(default=uuid4, editable=False, unique=True)
    aggregate_type = models.CharField(max_length=64, db_column="aggregatetype")
    aggregate_id = models.CharField(max_length=64, db_column="aggregateid")
    # Kafka partition key. Set to the owning user id so every event for a user
    # lands on one partition and is consumed in order, regardless of which
    # aggregate it touches. Debezium's EventRouter keys messages off this column.
    partition_key = models.CharField(max_length=64, db_column="partitionkey", default="")
    event_type = models.CharField(max_length=128, db_column="type")
    payload = models.JSONField()
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "outbox_events"
        indexes = [
            models.Index(fields=["aggregate_type", "aggregate_id"]),
        ]
