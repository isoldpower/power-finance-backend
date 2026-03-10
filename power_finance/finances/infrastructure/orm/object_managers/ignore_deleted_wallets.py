from django.db import models
from django.db.models import Q


class IgnoreDeletedWallets(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(
            Q(send_wallet__is_deleted__isnull=True) | Q(receive_wallet__is_deleted__isnull=True)
        )

    def with_deleted(self):
        return super().get_queryset()