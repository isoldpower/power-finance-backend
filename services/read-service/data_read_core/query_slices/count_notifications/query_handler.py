from .dtos import CountNotificationsQuery, NotificationCountsDTO
from .infra import count_notifications
from .logger_shortcuts import log_counts_served


class CountNotificationsQueryHandler:
    async def handle(self, query: CountNotificationsQuery) -> NotificationCountsDTO:
        unacknowledged, total = await count_notifications(query.user_id)
        log_counts_served(query.user_id, unacknowledged, total)

        return NotificationCountsDTO(
            unacknowledged=unacknowledged,
            total=total,
        )
