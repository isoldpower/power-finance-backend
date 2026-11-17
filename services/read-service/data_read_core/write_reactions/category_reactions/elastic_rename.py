from kafka_consumer_py import Effect, EventMessage
from kafka_messages import CategoryUpdated

from data_read_core.shared.elasticsearch import (
    TRANSACTIONS_INDEX,
    WALLETS_INDEX,
    get_elasticsearch,
)
from data_read_core.shared.postgres_orm import CategoryKinds

from .._logger_shortcuts import log_category_documents_renamed
from .._utilities import decode_payload

RENAME_SCRIPT = "ctx._source.category = params.new_name"


class RenameCategoryInDocuments(Effect):
    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, CategoryUpdated)
        index_name = (
            TRANSACTIONS_INDEX if payload.kind == CategoryKinds.TRANSACTION else WALLETS_INDEX
        )

        response = await get_elasticsearch().update_by_query(
            index=index_name,
            query={
                "bool": {
                    "filter": [
                        {"term": {"category_id": payload.category_id}},
                        {"term": {"user_id": payload.user_id}},
                    ]
                }
            },
            script={
                "source": RENAME_SCRIPT,
                "lang": "painless",
                "params": {"new_name": payload.new_name},
            },
            conflicts="proceed",
            refresh=True,
        )

        log_category_documents_renamed(
            payload.category_id,
            index_name,
            int(response.get("updated", 0)),
        )
