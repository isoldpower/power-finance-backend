from ..dtos import NotificationCountsDTO


def present_counts(counts: NotificationCountsDTO) -> dict:
    return {
        "unacknowledged": counts.unacknowledged,
        "total": counts.total,
    }
