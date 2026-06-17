from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class NotificationModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    short = models.CharField(max_length=120)
    message = models.TextField()
    payload = models.JSONField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")

    class Meta:
        db_table = "notifications"
        indexes = [
            models.Index(fields=["user", "is_read"]),
        ]
