import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from finances.domain.entities import WebhookType


class WebhookEventChoices(models.TextChoices):
    CREATE_TRANSACTION = WebhookType.TransactionCreate.value, "Transaction Created"
    UPDATE_TRANSACTION = WebhookType.TransactionUpdate.value, "Transaction Updated"
    DELETE_TRANSACTION = WebhookType.TransactionDelete.value, "Transaction Deleted"


class WebhookEndpointModel(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    url = models.URLField()
    secret = models.CharField(blank=False, null=False, max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="webhook_endpoints")

    class Meta:
        db_table = "finances_webhooks"


class WebhookDeliveryStatusChoices(models.TextChoices):
    INITIATED = "initiated", "Initiated"
    RETRY_SCHEDULED = "retry_scheduled", "Retry Scheduled"
    DELIVERED = "delivered", "Delivered"
    FAILED_PERMANENTLY = "failed_permanently", "Failed Permanently"


class WebhookDeliveryModel(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    status = models.CharField(
        choices=WebhookDeliveryStatusChoices.choices,
        default=WebhookDeliveryStatusChoices.INITIATED,
        max_length=64
    )
    endpoint = models.ForeignKey(
        WebhookEndpointModel,
        on_delete=models.PROTECT,
        related_name="deliveries",
    )
    event_id = models.UUIDField()
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    delivered_at = models.DateTimeField(blank=True, null=True)
    next_retry_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "finances_webhooks_deliveries"
        constraints = [
            models.UniqueConstraint(
                fields=["endpoint", "event_id"],
                name="unique_webhook_delivery_endpoint_event"
            ),
        ]
        indexes = [
            models.Index(fields=["endpoint"]),
            models.Index(fields=["status"]),
            models.Index(fields=["event_id"]),
            models.Index(fields=["event_id", "endpoint"]),
        ]


class WebhookDeliveryAttemptModel(models.Model):
    id = models.BigAutoField(primary_key=True)
    delivery = models.ForeignKey(
        WebhookDeliveryModel,
        on_delete=models.CASCADE,
        null=False,
        related_name="attempts",
    )
    attempt_number = models.PositiveIntegerField(blank=False, null=False)
    request_headers = models.JSONField(default=dict)
    request_body = models.JSONField(default=dict)
    response_status = models.IntegerField(blank=True, null=True)
    response_body = models.TextField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    started_at = models.DateTimeField(default=timezone.now)
    finished_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "finances_webhooks_delivery_attempts"
        constraints = [
            models.UniqueConstraint(
                fields=["delivery", "attempt_number"],
                name="unique_webhook_attempt_delivery_attempt"
            ),
        ]


class WebhookEventSubscriptionModel(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    endpoint = models.ForeignKey(
        WebhookEndpointModel,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    event_type = models.CharField(choices=WebhookEventChoices.choices, max_length=50)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "finances_webhook_event_subscriptions"
        constraints = [
            models.UniqueConstraint(
                fields=["endpoint", "event_type"],
                name="unique_webhook_subscription_endpoint_event_type"
            ),
        ]
        indexes = [
            models.Index(fields=["endpoint"]),
            models.Index(fields=["event_type"]),
            models.Index(fields=["endpoint", "event_type"]),
        ]