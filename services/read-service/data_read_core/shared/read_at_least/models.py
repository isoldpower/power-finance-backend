from django.db import models


class AppliedOutboxSeq(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    applied_seq = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "read_applied_outbox_seq"


class EsAppliedOutboxSeq(models.Model):
    user_id = models.BigIntegerField(primary_key=True)
    applied_seq = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "read_es_applied_outbox_seq"


class EsPendingOutboxSeq(models.Model):
    """An outbox seq whose search projection failed and has not been applied since.

    `applied_seq` is a high-water mark, so later events would otherwise carry it
    past a dead-lettered one and let Read-At-Least report a search index that is
    missing that write as caught up.
    """

    user_id = models.BigIntegerField()
    outbox_seq = models.BigIntegerField()
    event_id = models.CharField(max_length=128)
    failed_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "read_es_pending_outbox_seq"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "outbox_seq"],
                name="read_es_pending_outbox_seq_user_seq",
            ),
        ]
