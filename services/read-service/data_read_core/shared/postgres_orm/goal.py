from django.db import models


class GoalReadModel(models.Model):
    id = models.UUIDField(primary_key=True)
    user_id = models.BigIntegerField()
    title = models.CharField(max_length=255)
    currency_code = models.CharField(max_length=8)
    target = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    progress = models.DecimalField(max_digits=20, decimal_places=2, default=0)
    url = models.URLField(max_length=2048, null=True, blank=True)
    finish_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "read_goals"
        indexes = [
            models.Index(
                fields=["user_id", "-created_at", "-id"],
                include=["title", "currency_code", "target", "progress"],
                condition=models.Q(deleted_at__isnull=True),
                name="rg_user_keyset_idx",
            ),
        ]
