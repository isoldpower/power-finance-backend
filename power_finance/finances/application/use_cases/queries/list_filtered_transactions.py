import asyncio
from dataclasses import dataclass
from typing import Any
from django.db import InternalError

from finances.domain.entities import (
    FilterPolicy,
    ResolvedFilterTree,
    FilterFieldPolicy,
    ComparisonOperator,
    TypeVariant,
)
from finances.domain.exceptions import FilterParseError
from finances.domain.services import resolve_filter_query, resolve_filter_query_sql

from finances.domain.builders import WalletBuilder

from ...bootstrap import get_repository_registry
from ...dto_builders import transaction_to_plain_dto, wallet_to_dto
from ...dtos import TransactionPlainDTO
from ...interfaces import TransactionRepository, WalletRepository


@dataclass(frozen=True)
class ListFilteredTransactionsQuery:
    user_id: int
    filter_body: dict[str, Any]


class ListFilteredTransactionsQueryHandler:
    transaction_repository: TransactionRepository
    wallet_repository: WalletRepository
    filter_policy: FilterPolicy = {
        "id": FilterFieldPolicy(
            request_name="id",
            model_lookup="id",
            allowed_operators={ComparisonOperator.Equal},
            value_type=TypeVariant.UUID,
        ),
        "source_wallet_id": FilterFieldPolicy(
            request_name="source_wallet_id",
            model_lookup="source_wallet_id",
            allowed_operators={ComparisonOperator.Equal},
            value_type=TypeVariant.UUID,
        ),
        "amount": FilterFieldPolicy(
            request_name="amount",
            model_lookup="amount",
            allowed_operators={
                ComparisonOperator.Equal,
                ComparisonOperator.GreaterEqual,
                ComparisonOperator.LessEqual,
                ComparisonOperator.Greater,
                ComparisonOperator.Less,
            },
            value_type=TypeVariant.FLOAT,
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
            transaction_repository: TransactionRepository | None = None,
            wallet_repository: WalletRepository | None = None,
    ) -> None:
        registry = get_repository_registry()
        self.transaction_repository = transaction_repository or registry.transaction_repository
        self.wallet_repository = wallet_repository or registry.wallet_repository

    async def handle(self, request: ListFilteredTransactionsQuery) -> list[TransactionPlainDTO]:
        try:
            resolved_query = resolve_filter_query(request.filter_body, self.filter_policy)
            resolved_sql = resolve_filter_query_sql(request.filter_body, self.filter_policy)
            filter_tree = ResolvedFilterTree(
                django_query=resolved_query,
                raw_sql_query=resolved_sql,
                applied_policy=self.filter_policy,
            )
            filtered_transactions = await self.transaction_repository.list_transactions_with_filters(
                filter_tree,
                request.user_id
            )
            wallets = await asyncio.gather(*[
                self.wallet_repository.get_user_wallet_by_id(
                    wallet_id=transaction.source_wallet_id,
                    user_id=request.user_id,
                ) for transaction in filtered_transactions
            ])
            checkpoints = await asyncio.gather(*[
                self.transaction_repository.get_checkpoint(wallet.id)
                for wallet in wallets
            ])
            wallet_transactions = await asyncio.gather(*[
                self.transaction_repository.get_unsettled_transactions(
                    wallet.id, checkpoint.settled_at if checkpoint else None
                )
                for wallet, checkpoint in zip(wallets, checkpoints)
            ])
            wallets = [
                WalletBuilder(wallet)
                    .set_checkpoint(checkpoint)
                    .set_transactions(transactions)
                    .build_wallet()
                for wallet, checkpoint, transactions in zip(wallets, checkpoints, wallet_transactions)
            ]

            return [
                transaction_to_plain_dto(transaction, wallet_to_dto(wallets[i]))
                for i, transaction in enumerate(filtered_transactions)
            ]
        except FilterParseError as exception:
            raise exception
        except Exception as exception:
            raise InternalError() from exception
