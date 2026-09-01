from decimal import Decimal

from kafka_messages import (
    ActionSeverity as ProtoSeverity,
)
from kafka_messages import (
    ActionSource as ProtoSource,
)
from kafka_messages import (
    ActionStatus as ProtoStatus,
)
from kafka_messages import (
    ResolutionIntent as ProtoIntent,
)

from data_read_core.shared.postgres_orm import (
    ActionSeverity,
    ActionSource,
    ActionStatus,
)

_SOURCES: dict[int, str] = {
    ProtoSource.ACTION_SOURCE_ASSISTANT: ActionSource.ASSISTANT,
    ProtoSource.ACTION_SOURCE_SCHEDULER: ActionSource.SCHEDULER,
}
_SEVERITIES: dict[int, str] = {
    ProtoSeverity.ACTION_SEVERITY_INFO: ActionSeverity.INFO,
    ProtoSeverity.ACTION_SEVERITY_WARNING: ActionSeverity.WARNING,
    ProtoSeverity.ACTION_SEVERITY_CRITICAL: ActionSeverity.CRITICAL,
}
_STATUSES: dict[int, str] = {
    ProtoStatus.ACTION_STATUS_PENDING: ActionStatus.PENDING,
    ProtoStatus.ACTION_STATUS_RESOLVED: ActionStatus.RESOLVED,
    ProtoStatus.ACTION_STATUS_DISMISSED: ActionStatus.DISMISSED,
    ProtoStatus.ACTION_STATUS_EXPIRED: ActionStatus.EXPIRED,
}
_INTENTS: dict[int, str] = {
    ProtoIntent.RESOLUTION_INTENT_PRIMARY: "primary",
    ProtoIntent.RESOLUTION_INTENT_SECONDARY: "secondary",
    ProtoIntent.RESOLUTION_INTENT_DANGER: "danger",
}

SEVERITY_RANKS: dict[str, int] = {
    ActionSeverity.INFO: 1,
    ActionSeverity.WARNING: 2,
    ActionSeverity.CRITICAL: 3,
}


def source_of(source: int) -> str:
    return _SOURCES.get(source, ActionSource.ASSISTANT)


def severity_of(severity: int) -> str:
    return _SEVERITIES.get(severity, ActionSeverity.INFO)


def status_of(status: int) -> str:
    return _STATUSES.get(status, ActionStatus.PENDING)


def rank_of(severity: str) -> int:
    return SEVERITY_RANKS.get(
        severity,
        SEVERITY_RANKS[ActionSeverity.INFO],
    )


def money_of(raw: str) -> Decimal | None:
    return Decimal(raw) if raw else None


def resolutions_of(resolutions) -> list[dict]:
    return [
        {
            "resolution_id": resolution.resolution_id,
            "label": resolution.label,
            "intent": _INTENTS.get(
                resolution.intent,
                "secondary",
            ),
            "applies": resolution.applies,
        }
        for resolution in resolutions
    ]
