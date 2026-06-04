from logging import getLogger

from django.db import IntegrityError
from django.db.models import Value
from django.db.models.functions import Greatest

from .models import AppliedOutboxSeq

logger = getLogger("background_workers.write_message_consumer")


async def record_applied_seq(user_id: int, outbox_seq: int) -> None:
    """Bump the user's applied outbox seq to ``max(current, outbox_seq)``."""

    updated_record = await AppliedOutboxSeq.objects.filter(user_id=user_id).aupdate(
        applied_seq=Greatest("applied_seq", Value(outbox_seq)),
    )

    if not updated_record:
        await _create_new_record(user_id, outbox_seq)


async def _create_new_record(user_id: int, outbox_seq: int) -> None:
    try:
        await AppliedOutboxSeq.objects.acreate(
            user_id=user_id,
            applied_seq=outbox_seq,
        )
    except IntegrityError:
        await AppliedOutboxSeq.objects.filter(user_id=user_id).aupdate(
            applied_seq=Greatest("applied_seq", Value(outbox_seq)),
        )
    finally:
        logger.debug("Recorded applied outbox seq %s for user %s.", outbox_seq, user_id)
