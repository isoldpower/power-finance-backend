from django.db import models


class AppliedOutboxSeq(models.Model):
    """Highest write-side outbox seq the read side has projected for a user."""

    user_id = models.BigIntegerField(primary_key=True)
    applied_seq = models.BigIntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "read_applied_outbox_seq"
