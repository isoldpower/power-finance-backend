import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from finances.domain.entities import WebhookType
from finances.domain.events import WebhookDeliveryStatus


class WebhookEventChoices(models.TextChoices):
    CREATE_TRANSACTION = WebhookType.TransactionCreate.value, "Transaction Created"
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
    IN_PROGRESS = WebhookDeliveryStatus.IN_PROGRESS.value, "Initiated"
    RETRY_SCHEDULED = WebhookDeliveryStatus.RETRY_SCHEDULED.value, "Retry Scheduled"
    DELIVERED = WebhookDeliveryStatus.SUCCESS.value, "Delivered"
    FAILED_PERMANENTLY = WebhookDeliveryStatus.FAILED.value, "Failed Permanently"


class WebhookDeliveryModel(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    status = models.CharField(
        choices=WebhookDeliveryStatusChoices.choices,
        default=WebhookDeliveryStatusChoices.RETRY_SCHEDULED,
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
    next_retry_at = models.DateTimeField(default=timezone.now, blank=True, null=True)

    class Meta:
        db_table = "finances_webhooks_deliveries"
        constraints = [
            models.UniqueConstraint(
                fields=["endpoint", "event_id"],
                name="unique_webhook_delivery_endpoint_event"
            ),
        ]
        indexes = [
            models.Index(fields=["status", "next_retry_at"]),
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


class WebhookPayloadModel(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    hash = models.CharField(max_length=120)
    delivery = models.OneToOneField(WebhookDeliveryModel, on_delete=models.CASCADE)
    payload = models.JSONField(default=dict)
    headers = models.JSONField(default=dict)

    class Meta:
        db_table = "finances_webhook_payloads"
        constraints = [
            models.UniqueConstraint(
                fields=["delivery", "hash"],
                name="unique_webhook_payload_delivery"
            )
        ]
        indexes = [
            models.Index(fields=["delivery", "hash"]),
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