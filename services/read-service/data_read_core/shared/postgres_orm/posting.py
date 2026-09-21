from django.db import models


class AccountPostingReadModel(models.Model):
    id = models.UUIDField(primary_key=True)
    user_id = models.BigIntegerField()

    account_id = models.UUIDField()
    transaction_id = models.UUIDField()
    dispatch_id = models.UUIDField(null=True, blank=True)

    title = models.CharField(max_length=120, blank=True, default="")
    icon = models.CharField(max_length=64, blank=True, default="")
    debit = models.BooleanField()
    amount = models.DecimalField(max_digits=20, decimal_places=2)
    currency_code = models.CharField(max_length=8, blank=True, default="")
    position = models.IntegerField(default=0)

    created_at = models.DateTimeField()

    class Meta:
        db_table = "read_account_postings"
        indexes = [
            models.Index(
                fields=["account_id", "-created_at", "-id"],
                include=["amount", "currency_code", "debit", "title"],
                name="rap_account_keyset_idx",
            ),
            models.Index(
                fields=["transaction_id", "position"],
                name="rap_transaction_idx",
            ),
            models.Index(
                fields=["user_id"],
                name="rap_user_idx",
            ),
        ]


class AccountDispatchReadModel(models.Model):
    transaction_id = models.UUIDField(primary_key=True)
    user_id = models.BigIntegerField()
    dispatch_id = models.UUIDField()

    balanced = models.BooleanField(default=False)
    comment = models.CharField(max_length=255, blank=True, default="")
    backend = models.CharField(max_length=32, blank=True, default="")

    created_count = models.IntegerField(default=0)
    deleted_count = models.IntegerField(default=0)

    dispatched_at = models.DateTimeField()

    class Meta:
        db_table = "read_account_dispatches"
        indexes = [
            models.Index(fields=["user_id"], name="rad_user_idx"),
        ]
