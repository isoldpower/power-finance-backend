class RetryableWebhookDeliveryError(Exception):
    """Raised when webhook delivery should be retried by Celery."""

    def __init__(self, message: str, retry_after_seconds: int | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds