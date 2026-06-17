from django.db import models


class AppliedOutboxSeq(models.Model):
    """Highest write-side outbox seq the read side has projected for a user."""

    user_id = models.BigIntegerField(primary_key=True)
    applied_seq = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "read_applied_outbox_seq"


class EsAppliedOutboxSeq(models.Model):
    """Highest write-side outbox seq the Elasticsearch projection has applied
    for a user. Tracked separately because the ES projection group is a distinct
    pipeline from the Postgres one."""

    user_id = models.BigIntegerField(primary_key=True)
    applied_seq = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "read_es_applied_outbox_seq"
