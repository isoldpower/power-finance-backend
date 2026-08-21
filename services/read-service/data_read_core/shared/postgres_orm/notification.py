from django.db import models


class NotificationReadModel(models.Model):
    """Denormalised notification projection."""

    id = models.UUIDField(primary_key=True)
    user_id = models.BigIntegerField()
    short = models.CharField(max_length=120)
    message = models.TextField()
    payload = models.JSONField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "read_notifications"
        indexes = [
            models.Index(
                fields=["user_id", "-created_at", "-id"],
                name="rn_user_keyset_idx",
            ),
            models.Index(
                fields=["user_id", "is_read"],
                name="rn_user_unread_idx",
            ),
        ]
