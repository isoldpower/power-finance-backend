from datetime import datetime

from kafka_messages import (
    ActionRaised,
    ActionSeverity,
    ActionSource,
    ActionStatus,
    ResolutionIntent,
)
from kafka_messages import (
    ActionResolution as ActionResolutionMessage,
)
from kafka_messages import (
    ActionResolved as ActionResolvedMessage,
)

from data_write_core.domain.entities import (
    ActionEntity,
)
from data_write_core.domain.entities import (
    ActionSeverity as DomainSeverity,
)
from data_write_core.domain.entities import (
    ActionSource as DomainSource,
)
from data_write_core.domain.entities import (
    ActionStatus as DomainStatus,
)
from data_write_core.domain.value_objects import ResolutionIntent as DomainIntent
from data_write_core.infrastructure.messaging import (
    build_outbox_entry,
    datetime_to_timestamp,
)

ACTION_AGGREGATE = "action"

_SOURCES: dict[str, int] = {
    DomainSource.ASSISTANT: ActionSource.ACTION_SOURCE_ASSISTANT,
    DomainSource.SCHEDULER: ActionSource.ACTION_SOURCE_SCHEDULER,
}
_SEVERITIES: dict[str, int] = {
    DomainSeverity.INFO: ActionSeverity.ACTION_SEVERITY_INFO,
    DomainSeverity.WARNING: ActionSeverity.ACTION_SEVERITY_WARNING,
    DomainSeverity.CRITICAL: ActionSeverity.ACTION_SEVERITY_CRITICAL,
}
_STATUSES: dict[str, int] = {
    DomainStatus.PENDING: ActionStatus.ACTION_STATUS_PENDING,
    DomainStatus.RESOLVED: ActionStatus.ACTION_STATUS_RESOLVED,
    DomainStatus.DISMISSED: ActionStatus.ACTION_STATUS_DISMISSED,
    DomainStatus.EXPIRED: ActionStatus.ACTION_STATUS_EXPIRED,
}
_INTENTS: dict[str, int] = {
    DomainIntent.PRIMARY: ResolutionIntent.RESOLUTION_INTENT_PRIMARY,
    DomainIntent.SECONDARY: ResolutionIntent.RESOLUTION_INTENT_SECONDARY,
    DomainIntent.DANGER: ResolutionIntent.RESOLUTION_INTENT_DANGER,
}


def action_raised(action: ActionEntity):
    message = ActionRaised(
        action_id=action.unique_id,
        user_external_id=action.user_external_id,
        user_id=int(action.user_id),
        source=_SOURCES.get(
            action.source,
            ActionSource.ACTION_SOURCE_UNSPECIFIED,
        ),
        kind=action.kind,
        severity=_SEVERITIES.get(
            action.severity,
            ActionSeverity.ACTION_SEVERITY_INFO,
        ),
        title=action.title,
        body=action.body,
        subject_type=action.subject_type or "",
        subject_id=action.subject_id or "",
        money_amount=str(action.money_amount) if action.money_amount is not None else "",
        money_currency=action.money_currency or "",
        group_key=action.group_key or "",
        occurrences=action.occurrences,
        resolutions=[
            ActionResolutionMessage(
                resolution_id=resolution.resolution_id,
                label=resolution.label,
                intent=_INTENTS.get(
                    resolution.intent,
                    ResolutionIntent.RESOLUTION_INTENT_SECONDARY,
                ),
                applies=resolution.applies,
                dismissal=resolution.dismissal,
            )
            for resolution in action.resolutions
        ],
    )
    message.last_seen_at.FromDatetime(action.last_seen_at)
    message.created_at.FromDatetime(action.created_at)

    if action.expires_at is not None:
        message.expires_at.FromDatetime(action.expires_at)

    return build_outbox_entry(
        message,
        aggregate_type=ACTION_AGGREGATE,
        aggregate_id=action.unique_id,
        partition_key=action.user_external_id,
    )


def action_resolved(action: ActionEntity, *, at: datetime):
    message = ActionResolvedMessage(
        action_id=action.unique_id,
        user_external_id=action.user_external_id,
        user_id=int(action.user_id),
        status=_STATUSES.get(
            action.status,
            ActionStatus.ACTION_STATUS_RESOLVED,
        ),
        resolution_id=action.resolution_id or "",
        resolved_at=datetime_to_timestamp(at),
        updated_at=datetime_to_timestamp(at),
    )

    return build_outbox_entry(
        message,
        aggregate_type=ACTION_AGGREGATE,
        aggregate_id=action.unique_id,
        partition_key=action.user_external_id,
    )
