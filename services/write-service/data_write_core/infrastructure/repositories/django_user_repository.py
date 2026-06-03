from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.db import transaction
from kafka_messages import UserSynced

from data_write_core.application.interfaces import UserRepository
from data_write_core.domain.entities import InternalUserEntity
from data_write_core.infrastructure.messaging import build_outbox_entry
from data_write_core.infrastructure.orm import OutboxEntryModel

from .mappers import UserMapper


class DjangoUserRepository(UserRepository):
    def __init__(self):
        self._UserModel = get_user_model()

    async def get_synced_internal(self, external_id: str) -> InternalUserEntity:
        internal_user = await sync_to_async(self._get_or_create_with_outbox)(external_id)

        return UserMapper.to_domain(internal_user)

    def _get_or_create_with_outbox(self, external_id: str):
        with transaction.atomic():
            internal_user, created = self._UserModel.objects.get_or_create(
                username=external_id,
            )
            if created:
                self._append_user_synced(internal_user.id, external_id)

        return internal_user

    def _append_user_synced(self, user_id: int, external_id: str) -> None:
        entry = build_outbox_entry(
            UserSynced(user_id=user_id, external_id=external_id),
            aggregate_type="user",
            aggregate_id=str(user_id),
        )
        OutboxEntryModel.objects.create(
            event_id=entry.event_id,
            aggregate_type=entry.aggregate_type,
            aggregate_id=entry.aggregate_id,
            partition_key=entry.partition_key,
            event_type=entry.event_type,
            payload=entry.payload,
            occurred_at=entry.occurred_at,
        )
