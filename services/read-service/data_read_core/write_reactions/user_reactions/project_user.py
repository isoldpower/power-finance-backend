from logging import getLogger

from django.contrib.auth import get_user_model
from kafka_messages import UserSynced

from data_read_core.shared.kafka_updates import Effect, EventMessage

from .._utilities import decode_payload, handle_database_errors

logger = getLogger("background_workers.write_message_consumer")


class ProjectUserReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, UserSynced)
        await handle_database_errors(
            self._project_user,
            payload,
            resource_id=payload.user_id,
        )

    async def _project_user(self, payload: UserSynced) -> None:
        user_model = get_user_model()
        await user_model.objects.aupdate_or_create(
            id=payload.user_id,
            defaults={"username": payload.external_id},
        )
        logger.info(
            "Projected user %s (external %s).",
            payload.user_id,
            payload.external_id,
        )
