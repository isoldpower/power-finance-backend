from enum import StrEnum

from kafka_messages import NotificationSeverity


class Severity(StrEnum):
    SEVERITY_INFO = "info"
    SEVERITY_WARNING = "warning"
    SEVERITY_CRITICAL = "critical"


SEVERITIES: tuple[str, ...] = (
    Severity.SEVERITY_INFO,
    Severity.SEVERITY_WARNING,
    Severity.SEVERITY_CRITICAL,
)

_PROTO_BY_NAME: dict[str, int] = {
    Severity.SEVERITY_INFO: NotificationSeverity.NOTIFICATION_SEVERITY_INFO,
    Severity.SEVERITY_WARNING: NotificationSeverity.NOTIFICATION_SEVERITY_WARNING,
    Severity.SEVERITY_CRITICAL: NotificationSeverity.NOTIFICATION_SEVERITY_CRITICAL,
}

_NAME_BY_PROTO: dict[int, str] = {proto: name for name, proto in _PROTO_BY_NAME.items()}


def severity_to_proto(severity: str) -> int:
    return _PROTO_BY_NAME.get(
        severity,
        NotificationSeverity.NOTIFICATION_SEVERITY_INFO,
    )


def severity_from_proto(severity: int) -> str:
    return _NAME_BY_PROTO.get(
        severity,
        Severity.SEVERITY_INFO,
    )


def normalise_severity(raw: str | None) -> str:
    candidate = (raw or "").strip().lower()

    return candidate if candidate in SEVERITIES else Severity.SEVERITY_INFO
