from data_read_core.shared.filtering import FilterTree

from .dtos import SearchWebhooksQuery, WebhookDTO
from .infra import search_owned_webhooks
from .logger_shortcuts import log_search_served
from .policy import WEBHOOK_FILTER_POLICY


class SearchWebhooksQueryHandler:
    """Webhook configs are low-volume so search runs against the Postgres
    projection (no Elasticsearch index for webhooks)."""

    async def handle(self, query: SearchWebhooksQuery) -> tuple[list[WebhookDTO], int]:
        filter_query = FilterTree(WEBHOOK_FILTER_POLICY).resolve(query.filter_body)
        models, total = await search_owned_webhooks(
            user_id=query.user_id,
            filter_query=filter_query,
            limit=query.limit,
            offset=query.offset,
        )

        webhooks = [WebhookDTO.from_read_model(model) for model in models]
        log_search_served(query.user_id, len(webhooks), total)

        return webhooks, total
