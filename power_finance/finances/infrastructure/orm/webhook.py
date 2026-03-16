import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from finances.domain.entities import WebhookType


class WebhookEventChoices(models.TextChoices):
    CREATE_TRANSACTION = WebhookType.TransactionCreate.value


class WebhookEndpointModel(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    title = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    url = models.URLField()
    secret = models.CharField(blank=False, null=False, max_length=255)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        db_table = "finances_webhooks"


class WebhookDeliveryModel(models.Model):
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    response_status = models.IntegerField(null=True)
    error_message = models.TextField(null=True)
    endpoint = models.ForeignKey(WebhookEndpointModel, on_delete=models.PROTECT)

    class Meta:
        db_table = "finances_webhooks_deliveries"