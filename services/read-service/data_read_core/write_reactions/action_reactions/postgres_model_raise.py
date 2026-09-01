from datetime import UTC

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import ActionRaised

from data_read_core.shared.postgres_orm import ActionReadModel

from .._logger_shortcuts import log_action_postgres_raised
from .._utilities import decode_payload, handle_database_errors
from ._utilities import (
    money_of,
    rank_of,
    resolutions_of,
    severity_of,
    source_of,
)


class RaiseActionReadModel(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, ActionRaised)
        await handle_database_errors(
            self._record_action,
            payload,
            resource_id=payload.action_id,
        )

    async def _record_action(self, payload: ActionRaised) -> None:
        severity = severity_of(payload.severity)
        created_at = payload.created_at.ToDatetime(tzinfo=UTC)
        fields = {
            "user_id": payload.user_id,
            "source": source_of(payload.source),
            "kind": payload.kind,
            "severity": severity,
            "severity_rank": rank_of(severity),
            "title": payload.title,
            "body": payload.body,
            "subject_type": payload.subject_type,
            "subject_id": payload.subject_id,
            "money_amount": money_of(payload.money_amount),
            "money_currency": payload.money_currency,
            "group_key": payload.group_key,
            "occurrences": payload.occurrences,
            "last_seen_at": payload.last_seen_at.ToDatetime(tzinfo=UTC),
            "expires_at": (
                payload.expires_at.ToDatetime(tzinfo=UTC)
                if payload.HasField("expires_at")
                else None
            ),
            "resolutions": resolutions_of(payload.resolutions),
        }

        await ActionReadModel.objects.aupdate_or_create(
            id=payload.action_id,
            defaults=fields,
            create_defaults={**fields, "created_at": created_at},
        )
        log_action_postgres_raised(
            payload.action_id,
            payload.occurrences,
        )
