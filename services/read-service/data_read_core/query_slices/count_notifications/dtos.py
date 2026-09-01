from dataclasses import dataclass


@dataclass(frozen=True)
class CountNotificationsQuery:
    user_id: int


@dataclass(frozen=True)
class NotificationCountsDTO:
    unacknowledged: int
    total: int
