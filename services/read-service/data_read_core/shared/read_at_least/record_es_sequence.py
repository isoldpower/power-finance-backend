from django.db import IntegrityError
from django.db.models import Value
from django.db.models.functions import Greatest

from .logger_shortcuts import log_recorded_es_outbox_sequence
from .models import EsAppliedOutboxSeq


async def record_es_applied_seq(user_id: int, outbox_seq: int) -> None:
    """Bump the user's ES-applied outbox seq to ``max(current, outbox_seq)``."""

    updated_record = await EsAppliedOutboxSeq.objects.filter(user_id=user_id).aupdate(
        applied_seq=Greatest("applied_seq", Value(outbox_seq))
    )

    if not updated_record:
        await _create_new_record(user_id, outbox_seq)


async def _create_new_record(user_id: int, outbox_seq: int) -> None:
    try:
        await EsAppliedOutboxSeq.objects.acreate(
            user_id=user_id,
            applied_seq=outbox_seq,
        )
    except IntegrityError:
        await EsAppliedOutboxSeq.objects.filter(user_id=user_id).aupdate(
            applied_seq=Greatest("applied_seq", Value(outbox_seq)),
        )
    finally:
        log_recorded_es_outbox_sequence(outbox_seq, user_id)
