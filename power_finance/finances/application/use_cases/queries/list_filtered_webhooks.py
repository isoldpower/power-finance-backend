from uuid import UUID
from datetime import datetime
from dataclasses import dataclass
from typing import Any

from django.core.exceptions import ObjectDoesNotExist

from finances.domain.entities.filter import (
    FilterPolicy, 
    ResolvedFilterTree, 
    FilterFieldPolicy,
    ComparisonOperator
)
from finances.domain.services import resolve_filter_query
from finances.infrastructure.repositories import DjangoWebhookRepository

from ...dto_builders import webhook_to_dto
from ...dtos import WebhookDTO
from ...interfaces import WebhookRepository


@dataclass(frozen=True)
class ListFilteredWebhooksQuery:
    user_id: int
    filter_body: dict[str, Any]


class ListFilteredWebhooksQueryHandler:
    webhooks_repository: WebhookRepository
    filter_policy: FilterPolicy = {
        "id": FilterFieldPolicy(
            request_name="id",
            model_lookup="id",
            allowed_operators={ComparisonOperator.Equal},
            value_type=UUID,
        ),
        "title": FilterFieldPolicy(
            request_name="title",
            model_lookup="title",
            allowed_operators={
                ComparisonOperator.Equal,
                ComparisonOperator.Contains,
                ComparisonOperator.IContains,
            },
            value_type=str,
        ),
        "url": FilterFieldPolicy(
            request_name="url",
            model_lookup="url",
            allowed_operators={
                ComparisonOperator.Equal,
                ComparisonOperator.Contains,
                ComparisonOperator.IContains,
            },
            value_type=str,
        ),
        "is_active": FilterFieldPolicy(
            request_name="is_active",
            model_lookup="is_active",
            allowed_operators={ComparisonOperator.Equal},
            value_type=bool,
        ),
        "created_at": FilterFieldPolicy(
            request_name="created_at",
            model_lookup="created_at",
            allowed_operators={
                ComparisonOperator.Equal,
                ComparisonOperator.GreaterEqual,
                ComparisonOperator.LessEqual,
                ComparisonOperator.Greater,
                ComparisonOperator.Less,
            },
            value_type=str,
        ),
    }

    def __init__(
            self,
            webhooks_repository: WebhookRepository | None = None,
    ) -> None:
        self.webhooks_repository = webhooks_repository or DjangoWebhookRepository()

    def handle(self, request: ListFilteredWebhooksQuery) -> list[WebhookDTO]:
        try:
            resolved_query = resolve_filter_query(request.filter_body, self.filter_policy)
            filter_tree = ResolvedFilterTree(
                query=resolved_query,
                applied_policy=self.filter_policy,
            )
            filtered_webhooks = self.webhooks_repository.list_webhooks_with_filters(filter_tree, request.user_id)

            return [webhook_to_dto(webhook) for webhook in filtered_webhooks]
        except ObjectDoesNotExist as e:
            raise ObjectDoesNotExist(f"Requested webhook does not exist: {e}")
