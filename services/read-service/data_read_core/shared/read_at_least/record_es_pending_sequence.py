from datetime import datetime

from .logger_shortcuts import log_cleared_es_pending_seq, log_recorded_es_pending_seq
from .models import EsPendingOutboxSeq


async def record_es_pending_seq(user_id: int, outbox_seq: int, event_id: str) -> None:
    await EsPendingOutboxSeq.objects.aupdate_or_create(
        user_id=user_id,
        outbox_seq=outbox_seq,
        defaults={"event_id": event_id},
    )
    log_recorded_es_pending_seq(outbox_seq, user_id, event_id)


async def clear_es_pending_seq(user_id: int, outbox_seq: int) -> None:
    deleted_count, _ = await EsPendingOutboxSeq.objects.filter(
        user_id=user_id,
        outbox_seq=outbox_seq,
    ).adelete()

    if deleted_count:
        log_cleared_es_pending_seq(outbox_seq, user_id)


async def clear_es_pending_seqs_failed_before(moment: datetime) -> int:
    deleted_count, _ = await EsPendingOutboxSeq.objects.filter(failed_at__lt=moment).adelete()

    return deleted_count
