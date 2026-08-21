from data_read_core.shared.http_contract import NotFound


class WebhookNotFoundError(NotFound):
    """404, including when the row exists but belongs to someone else."""

    message = "Webhook does not exist"
