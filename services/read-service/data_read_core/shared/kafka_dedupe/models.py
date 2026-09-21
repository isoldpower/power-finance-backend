from django.db import models
from django.utils import timezone


class KafkaConsumedEvent(models.Model):
    pk = models.CompositePrimaryKey("consumer_group", "event_id")
    consumer_group = models.TextField()
    event_id = models.TextField()
    consumed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "kafka_consumed_events"
        indexes = [
            models.Index(fields=["consumed_at"], name="kafka_consumed_at_idx"),
        ]
