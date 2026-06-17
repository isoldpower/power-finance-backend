from read_at_least_py import AppliedSeqReader

from .models import AppliedOutboxSeq


class DjangoAppliedSeqReader(AppliedSeqReader):
    """``AppliedSeqReader`` backed by the ``read_applied_outbox_seq`` table."""

    async def applied_seq(self, scope: str) -> int | None:
        return (
            await AppliedOutboxSeq.objects.filter(user_id=int(scope))
            .values_list("applied_seq", flat=True)
            .afirst()
        )
