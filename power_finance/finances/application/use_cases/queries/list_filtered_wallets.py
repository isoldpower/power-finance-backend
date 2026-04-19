import asyncio
from dataclasses import dataclass
from typing import Any

from finances.domain.entities import (
    FilterPolicy,
    ResolvedFilterTree,
    FilterFieldPolicy,
    ComparisonOperator,
    TypeVariant,
)
from finances.domain.services import resolve_filter_query, resolve_filter_query_sql

from finances.domain.builders import WalletBuilder

from ...bootstrap import get_repository_registry
from ...dto_builders import wallet_to_dto
from ...dtos import WalletDTO
from ...interfaces import WalletRepository, TransactionRepository


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
            transaction_repository: TransactionRepository | None = None,
    ) -> None:
        registry = get_repository_registry()
        self.wallet_repository = wallet_repository or registry.wallet_repository
        self.transaction_repository = transaction_repository or registry.transaction_repository

    async def handle(self, request: ListFilteredWalletsQuery) -> list[WalletDTO]:
        try:
            resolved_query = resolve_filter_query(request.filter_body, self.filter_policy)
            resolved_sql = resolve_filter_query_sql(request.filter_body, self.filter_policy)
            filter_tree = ResolvedFilterTree(
                django_query=resolved_query,
                raw_sql_query=resolved_sql,
                applied_policy=self.filter_policy,
            )
            filtered_wallets = await self.wallet_repository.list_wallets_with_filters(
                filter_tree,
                request.user_id
            )
            checkpoints = await asyncio.gather(*[
                self.transaction_repository.get_checkpoint(wallet.id)
                for wallet in filtered_wallets
            ])
            wallet_transactions = await asyncio.gather(*[
                self.transaction_repository.get_unsettled_transactions(
                    wallet.id, checkpoint.settled_at if checkpoint else None
                )
                for wallet, checkpoint in zip(filtered_wallets, checkpoints)
            ])
            filtered_wallets = [
                WalletBuilder(wallet)
                    .set_checkpoint(checkpoint)
                    .set_transactions(transactions)
                    .build_wallet()
                for wallet, checkpoint, transactions in zip(filtered_wallets, checkpoints, wallet_transactions)
            ]

            return [wallet_to_dto(wallet) for wallet in filtered_wallets]
        except Exception as e:
            raise e
