from data_read_core.shared.filtering import WEBHOOK_FILTER_POLICY, FilterTree
from data_read_core.shared.query_results import FetchedRows

from .dtos import SearchWebhooksQuery, WebhookDTO
from .infra import search_owned_webhooks
from .logger_shortcuts import log_search_served


class SearchWebhooksQueryHandler:
    """Webhook configs are low-volume so search runs against the Postgres
    projection (no Elasticsearch index for webhooks)."""

    async def handle(self, query: SearchWebhooksQuery) -> FetchedRows:
        filter_query = FilterTree(WEBHOOK_FILTER_POLICY).resolve(query.filter_body)
        models, total = await search_owned_webhooks(
            user_id=query.user_id,
            filter_query=filter_query,
            page=query.page,
        )

        webhooks = [WebhookDTO.from_read_model(model) for model in models]
        log_search_served(query.user_id, len(webhooks), total)

        return FetchedRows(
            rows=webhooks,
            total=total,
            cached=False,
        )
