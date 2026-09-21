from data_read_core.shared.http_contract import NotFound


class WebhookNotFoundError(NotFound):
    message = "Webhook does not exist"
