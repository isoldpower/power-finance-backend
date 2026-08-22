from datetime import UTC

from kafka_messages import TransactionMetadataUpdated

from data_read_core.shared.kafka_updates import Effect, EventMessage
from data_read_core.shared.postgres_orm import TransactionReadModel

from .._logger_shortcuts import log_transaction_postgres_metadata_updated
from .._utilities import decode_payload, handle_database_errors


class UpdateTransactionMetadataReadModel(Effect):
    """A PATCH. Touches no money — the amount is folded from the ledger, and
    nothing in this event carries one."""

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, TransactionMetadataUpdated)
        await handle_database_errors(
            self._update_metadata,
            payload,
            resource_id=payload.transaction_id,
        )

    async def _update_metadata(self, payload: TransactionMetadataUpdated) -> None:
        updated_row = await TransactionReadModel.objects.filter(id=payload.transaction_id).aupdate(
            name=payload.name,
            category=payload.category or None,
            evidence_url=payload.evidence_url or None,
            updated_at=payload.updated_at.ToDatetime(tzinfo=UTC),
        )
        log_transaction_postgres_metadata_updated(
            payload.transaction_id,
            updated_row,
        )
