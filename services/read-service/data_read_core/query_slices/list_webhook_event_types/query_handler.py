from webhook_catalog_py import event_types

from data_read_core.shared.query_results import FetchedRows

from .dtos import ListWebhookEventTypesQuery, WebhookEventTypeDTO
from .logger_shortcuts import log_served_from_catalog


class ListWebhookEventTypesQueryHandler:
    async def handle(self, query: ListWebhookEventTypesQuery) -> FetchedRows:
        catalog = [WebhookEventTypeDTO.from_catalog(entry) for entry in event_types()]

        log_served_from_catalog(len(catalog))

        return FetchedRows(
            rows=catalog,
            total=len(catalog),
            cached=False,
        )
