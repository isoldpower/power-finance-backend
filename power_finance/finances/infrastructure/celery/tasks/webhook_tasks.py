from uuid import UUID
from celery import shared_task
from celery.utils.log import get_task_logger

from finances.application.bootstrap import get_repository_registry
from finances.application.use_cases import WebhookDeliveryAttemptHandler

logger = get_task_logger(__name__)


@shared_task(name="finances.attempt_webhook_delivery")
def attempt_webhook_delivery(
        webhook_id: str,
        delivery_id: str,
) -> None:
    logger.info("Task [finances.attempt_webhook_delivery]: Starting delivery for Webhook: %s, Delivery: %s", webhook_id, delivery_id)
    handler = WebhookDeliveryAttemptHandler()
    registry = get_repository_registry()

    try:
        webhook = registry.webhook_repository.get_webhook_by_id(webhook_id=UUID(webhook_id))
        handler.handle(webhook=webhook, delivery_id=UUID(delivery_id))
        logger.info("Task [finances.attempt_webhook_delivery]: Successfully processed Delivery: %s", delivery_id)
    except Exception as exc:
        logger.error("Task [finances.attempt_webhook_delivery]: Error occurred for Delivery: %s - %s", delivery_id, str(exc))


@shared_task(name="finances.schedule_due_webhook_retries")
def schedule_due_webhook_retries() -> None:
    logger.info("Task [finances.schedule_due_webhook_retries]: Checking for deliveries to retry")

    try:
        registry = get_repository_registry()
        deliveries = registry.delivery_repository.get_deliveries_to_retry(limit=100)

        logger.info("Task [finances.schedule_due_webhook_retries]: Found %d deliveries to retry", len(deliveries))
        for delivery in deliveries:
            attempt_webhook_delivery.delay(
                webhook_id=str(delivery.endpoint_id),
                delivery_id=str(delivery.id),
            )
    except Exception as exc:
        logger.error("Task [finances.schedule_due_webhook_retries]: Error occurred for celery beat - %s", str(exc))