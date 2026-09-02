from webhook_catalog_py import event_types

from data_read_core.shared.query_results import FetchedRows

from .dtos import ListWebhookEventTypesQuery, WebhookEventTypeDTO
from .logger_shortcuts import log_served_from_catalog


class ListWebhookEventTypesQueryHandler:
    """No store and no cache: the catalog is a shared library table read from
    process memory, and it is the same table the publisher maps outbox events
    through, so serving it from anywhere else would let the two drift."""

    async def handle(self, query: ListWebhookEventTypesQuery) -> FetchedRows:
        catalog = [WebhookEventTypeDTO.from_catalog(entry) for entry in event_types()]

        log_served_from_catalog(len(catalog))

        return FetchedRows(
            rows=catalog,
            total=len(catalog),
            cached=False,
        )
