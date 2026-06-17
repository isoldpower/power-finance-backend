from read_at_least_py import AppliedSeqReader

from .models import EsAppliedOutboxSeq


class DjangoEsAppliedSeqReader(AppliedSeqReader):
    """``AppliedSeqReader`` backed by the ``read_es_applied_outbox_seq`` table."""

    async def applied_seq(self, scope: str) -> int | None:
        return (
            await EsAppliedOutboxSeq.objects.filter(user_id=int(scope))
            .values_list("applied_seq", flat=True)
            .afirst()
        )
