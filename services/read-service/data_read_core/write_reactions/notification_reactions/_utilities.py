from kafka_messages import NotificationSeverity

from data_read_core.shared.postgres_orm import Severity

_SEVERITY_NAMES: dict[int, Severity] = {
    NotificationSeverity.NOTIFICATION_SEVERITY_INFO: Severity.SEVERITY_INFO,
    NotificationSeverity.NOTIFICATION_SEVERITY_WARNING: Severity.SEVERITY_WARNING,
    NotificationSeverity.NOTIFICATION_SEVERITY_CRITICAL: Severity.SEVERITY_CRITICAL,
}


def severity_from_proto(severity: int) -> Severity:
    return _SEVERITY_NAMES.get(severity, Severity.SEVERITY_INFO)
