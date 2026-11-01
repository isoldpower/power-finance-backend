from read_at_least_py import AppliedSeqReader

from .models import EsAppliedOutboxSeq, EsPendingOutboxSeq


class DjangoEsAppliedSeqReader(AppliedSeqReader):
    """Reports the highest seq below which every search projection has landed."""

    async def applied_seq(self, scope: str) -> int | None:
        user_id = int(scope)
        applied = (
            await EsAppliedOutboxSeq.objects.filter(user_id=user_id)
            .values_list("applied_seq", flat=True)
            .afirst()
        )
        if applied is None:
            return None

        lowest_pending = (
            await EsPendingOutboxSeq.objects.filter(user_id=user_id)
            .order_by("outbox_seq")
            .values_list("outbox_seq", flat=True)
            .afirst()
        )
        if lowest_pending is None:
            return applied

        return min(applied, lowest_pending - 1)
