from django.db import models


class AutomationReadModel(models.Model):
    """A user-authored rule, projected."""

    id = models.UUIDField(primary_key=True)
    user_id = models.BigIntegerField()

    name = models.CharField(max_length=120)
    icon = models.CharField(max_length=64, blank=True, default="")
    enabled = models.BooleanField(default=True)

    trigger_type = models.CharField(max_length=16)
    trigger_event = models.CharField(max_length=32, blank=True, default="")
    trigger_schedule = models.CharField(max_length=16, blank=True, default="")
    filter_body = models.JSONField(null=True, blank=True)

    effects = models.JSONField(default=list)

    last_run_at = models.DateTimeField(null=True, blank=True)
    runs = models.IntegerField(default=0)

    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "read_automations"
        indexes = [
            models.Index(
                fields=["user_id", "-created_at", "-id"],
                include=["name", "enabled"],
                condition=models.Q(deleted_at__isnull=True),
                name="rau_user_keyset_idx",
            ),
            models.Index(
                fields=["user_id", "enabled"],
                name="rau_user_enabled_idx",
            ),
        ]
