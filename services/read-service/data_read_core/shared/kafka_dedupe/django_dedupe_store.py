from datetime import datetime

import psycopg
from django.utils import timezone
from kafka_client_py import DedupeStore

from .models import KafkaConsumedEvent


class DjangoDedupeStore(DedupeStore):
    def __init__(self, consumer_group: str) -> None:
        self._consumer_group = consumer_group

    async def seen(self, event_id: str) -> bool:
        return await KafkaConsumedEvent.objects.filter(
            consumer_group=self._consumer_group,
            event_id=event_id,
        ).aexists()

    async def mark(
        self,
        event_id: str,
        *,
        connection: psycopg.AsyncConnection | None = None,
        consumed_at: datetime | None = None,
    ) -> None:
        await KafkaConsumedEvent.objects.abulk_create(
            [
                KafkaConsumedEvent(
                    consumer_group=self._consumer_group,
                    event_id=event_id,
                    consumed_at=consumed_at or timezone.now(),
                )
            ],
            ignore_conflicts=True,
        )
