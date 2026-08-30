from django.contrib.auth import get_user_model
from kafka_consumer_py import Effect, EventMessage
from kafka_messages import UserSynced

from .._logger_shortcuts import log_user_projected
from .._utilities import decode_payload, handle_database_errors


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
        log_user_projected(payload.user_id, payload.external_id)
