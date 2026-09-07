from data_read_core.shared.http_contract import NotFound


class NotificationNotFoundError(NotFound):
    message = "Notification does not exist"
