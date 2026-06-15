from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class WebhookModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    title = models.CharField(max_length=120)
    url = models.URLField()
    secret = models.CharField(max_length=128)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="webhooks")

    class Meta:
        db_table = "webhooks"
        indexes = [
            models.Index(fields=["user", "-created_at"]),
        ]


class WebhookSubscriptionModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    webhook = models.ForeignKey(
        WebhookModel,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    event_type = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "webhook_subscriptions"
        constraints = [
            models.UniqueConstraint(
                fields=["webhook", "event_type"],
                name="uniq_webhook_event_type",
            ),
        ]
