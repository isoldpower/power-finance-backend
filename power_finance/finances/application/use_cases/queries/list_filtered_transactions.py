from uuid import UUID
from dataclasses import dataclass
from typing import Any

from finances.domain.entities import (
    FilterPolicy, 
    ResolvedFilterTree, 
    FilterFieldPolicy,
    ComparisonOperator
)
from finances.domain.services import resolve_filter_query
from finances.infrastructure.repositories import DjangoTransactionRepository

from ...dto_builders import transaction_to_plain_dto
from ...dtos import TransactionPlainDTO
from ...interfaces import TransactionRepository


@dataclass(frozen=True)
class ListFilteredTransactionsQuery:
    user_id: int
    filter_body: dict[str, Any]


class ListFilteredTransactionsQueryHandler:
    transaction_repository: TransactionRepository
    filter_policy: FilterPolicy = {
        "id": FilterFieldPolicy(
            request_name="id",
            model_lookup="id",
            allowed_operators={ComparisonOperator.Equal},
            value_type=UUID,
        ),
        "description": FilterFieldPolicy(
            request_name="description",
            model_lookup="description",
            allowed_operators={
                ComparisonOperator.Equal,
                ComparisonOperator.Contains,
                ComparisonOperator.IContains,
            },
            value_type=str,
        ),
        "type": FilterFieldPolicy(
            request_name="type",
            model_lookup="type",
            allowed_operators={ComparisonOperator.Equal},
            value_type=str,
        ),
        "category": FilterFieldPolicy(
            request_name="category",
            model_lookup="category",
            allowed_operators={ComparisonOperator.Equal},
            value_type=str,
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
        "sender_id": FilterFieldPolicy(
            request_name="sender_id",
            model_lookup="send_wallet_id",
            allowed_operators={ComparisonOperator.Equal},
            value_type=UUID,
        ),
        "receiver_id": FilterFieldPolicy(
            request_name="receiver_id",
            model_lookup="receive_wallet_id",
            allowed_operators={ComparisonOperator.Equal},
            value_type=UUID,
        ),
        "sender_amount": FilterFieldPolicy(
            request_name="sender_amount",
            model_lookup="send_amount",
            allowed_operators={
                ComparisonOperator.Equal,
                ComparisonOperator.GreaterEqual,
                ComparisonOperator.LessEqual,
                ComparisonOperator.Greater,
                ComparisonOperator.Less,
            },
            value_type=float,
        ),
        "receiver_amount": FilterFieldPolicy(
            request_name="receiver_amount",
            model_lookup="receive_amount",
            allowed_operators={
                ComparisonOperator.Equal,
                ComparisonOperator.GreaterEqual,
                ComparisonOperator.LessEqual,
                ComparisonOperator.Greater,
                ComparisonOperator.Less,
            },
            value_type=float,
        ),
    }

    def __init__(
            self,
            transaction_repository: TransactionRepository | None = None,
    ) -> None:
        self.transaction_repository = transaction_repository or DjangoTransactionRepository()

    def handle(self, request: ListFilteredTransactionsQuery) -> list[TransactionPlainDTO]:
        try:
            resolved_query = resolve_filter_query(request.filter_body, self.filter_policy)
            filter_tree = ResolvedFilterTree(
                query=resolved_query,
                applied_policy=self.filter_policy,
            )
            filtered_transactions = self.transaction_repository.list_transactions_with_filters(filter_tree, request.user_id)

            return [transaction_to_plain_dto(transaction) for transaction in filtered_transactions]
        except Exception as e:
            raise e
