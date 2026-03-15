from django.db import models
from django.db.models import Q


class IgnoreDeletedWallets(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(
            send_wallet__deleted_at__isnull=True,
            receive_wallet__deleted_at__isnull=True
        )

    def with_deleted(self):
        return super().get_queryset()

    def delete(self):
        self.get_queryset().delete()