from dataclasses import dataclass
from typing import Any

from finances.domain.entities import (
    FilterPolicy, 
    ResolvedFilterTree, 
    FilterFieldPolicy,
    ComparisonOperator,
    TypeVariant,
)
from finances.domain.services import resolve_filter_query

from ...bootstrap import get_repository_registry
from ...dto_builders import wallet_to_dto
from ...dtos import WalletDTO
from ...interfaces import WalletRepository


@dataclass(frozen=True)
class ListFilteredWalletsQuery:
    user_id: int
    filter_body: dict[str, Any]


class ListFilteredWalletsQueryHandler:
    wallet_repository: WalletRepository
    filter_policy: FilterPolicy = {
        "id": FilterFieldPolicy(
            request_name="id",
            model_lookup="id",
            allowed_operators={ComparisonOperator.Equal},
            value_type=TypeVariant.UUID,
        ),
        "name": FilterFieldPolicy(
            request_name="name",
            model_lookup="name",
            allowed_operators={
                ComparisonOperator.Equal,
                ComparisonOperator.Contains,
                ComparisonOperator.IContains,
            },
            value_type=TypeVariant.STRING,
        ),
        "credit": FilterFieldPolicy(
            request_name="credit",
            model_lookup="credit",
            allowed_operators={ComparisonOperator.Equal},
            value_type=TypeVariant.BOOLEAN,
        ),
        "amount": FilterFieldPolicy(
            request_name="amount",
            model_lookup="balance_amount",
            allowed_operators={
                ComparisonOperator.Equal,
                ComparisonOperator.GreaterEqual,
                ComparisonOperator.LessEqual,
                ComparisonOperator.Greater,
                ComparisonOperator.Less,
            },
            value_type=TypeVariant.FLOAT,
        ),
        "currency_code": FilterFieldPolicy(
            request_name="currency_code",
            model_lookup="currency_id",
            allowed_operators={ComparisonOperator.Equal},
            value_type=TypeVariant.STRING,
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
            value_type=TypeVariant.DATETIME,
        ),
    }

    def __init__(
            self,
            wallet_repository: WalletRepository | None = None,
    ) -> None:
        registry = get_repository_registry()
        self.wallet_repository = wallet_repository or registry.wallet_repository

    def handle(self, request: ListFilteredWalletsQuery) -> list[WalletDTO]:
        try:
            resolved_query = resolve_filter_query(request.filter_body, self.filter_policy)
            filter_tree = ResolvedFilterTree(
                query=resolved_query,
                applied_policy=self.filter_policy,
            )
            filtered_wallets = self.wallet_repository.list_wallets_with_filters(filter_tree, request.user_id)

            return [wallet_to_dto(wallet) for wallet in filtered_wallets]
        except Exception as e:
            raise e
