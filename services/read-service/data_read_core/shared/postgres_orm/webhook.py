from django.db import models


class WebhookReadModel(models.Model):
    """Denormalised webhook endpoint projection. The signing secret is
    deliberately NOT projected — reads never expose it; only the
    webhook-service consumes it from the config events."""

    id = models.UUIDField(primary_key=True)
    user_id = models.BigIntegerField()
    title = models.CharField(max_length=120)
    url = models.URLField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "read_webhooks"
        indexes = [
            models.Index(
                fields=["user_id", "-created_at"],
                name="rwh_user_created_idx",
            ),
        ]


class WebhookSubscriptionReadModel(models.Model):
    id = models.UUIDField(primary_key=True)
    webhook = models.ForeignKey(
        WebhookReadModel,
        on_delete=models.CASCADE,
        related_name="subscriptions",
    )
    user_id = models.BigIntegerField()
    event_type = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "read_webhook_subscriptions"
        indexes = [
            models.Index(
                fields=["webhook", "created_at"],
                name="rwhs_webhook_created_idx",
            ),
        ]
