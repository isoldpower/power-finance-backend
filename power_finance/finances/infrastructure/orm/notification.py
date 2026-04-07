import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class NotificationModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    short = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False)
    received_at = models.DateTimeField(editable=False, null=True, blank=True)

    class Meta:
        db_table = "finances_notifications"
        ordering = ["-created_at"]
