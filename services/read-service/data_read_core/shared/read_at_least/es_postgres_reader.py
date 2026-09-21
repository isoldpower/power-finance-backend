from read_at_least_py import AppliedSeqReader

from .models import EsAppliedOutboxSeq


class DjangoEsAppliedSeqReader(AppliedSeqReader):
    async def applied_seq(self, scope: str) -> int | None:
        return (
            await EsAppliedOutboxSeq.objects.filter(user_id=int(scope))
            .values_list("applied_seq", flat=True)
            .afirst()
        )
