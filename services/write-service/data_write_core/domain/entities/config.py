from datetime import timedelta
from enum import StrEnum


class NotificationDefaults(StrEnum):
    SEVERITY = "info"


SECRET_GRACE_PERIOD = timedelta(hours=24)
