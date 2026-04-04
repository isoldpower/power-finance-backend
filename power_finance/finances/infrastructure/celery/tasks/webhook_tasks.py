from uuid import UUID

from celery import shared_task

from finances.application.bootstrap import get_repository_registry
from finances.application.use_cases import WebhookDeliveryAttemptHandler


@shared_task(name="finances.attempt_webhook_delivery")
def attempt_webhook_delivery(
        webhook_id: str,
        delivery_id: str,
) -> None:
    handler = WebhookDeliveryAttemptHandler()
    registry = get_repository_registry()
    webhook = registry.webhook_repository.get_webhook_by_id(webhook_id=UUID(webhook_id))

    try:
        handler.handle(webhook=webhook, delivery_id=delivery_id)
    except Exception as exc:
        print(f"Error occurred under the attempt_webhook_delivery task:\n {exc}")


@shared_task(name="finances.schedule_due_webhook_retries")
def schedule_due_webhook_retries() -> None:
    registry = get_repository_registry()
    delivery_repository = registry.delivery_repository

    deliveries = delivery_repository.get_deliveries_to_retry(limit=100)

    for delivery in deliveries:
        attempt_webhook_delivery.delay(
            webhook_id=str(delivery.endpoint_id),
            delivery_id=str(delivery.id),
        )