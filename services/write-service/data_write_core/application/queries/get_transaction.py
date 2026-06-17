from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from ..bootstrap import get_repository_registry
from ..dtos import TransactionPlainDTO
from ..exceptions import FallbackTransactionNotVisibleError
from ..interfaces import TransactionRepository, WalletRepository


@dataclass(frozen=True)
class GetFallbackTransactionQuery:
    user_id: int
    transaction_id: UUID


class GetFallbackTransactionQueryHandler:
    def __init__(
        self,
        transaction_repository: TransactionRepository | None = None,
        wallet_repository: WalletRepository | None = None,
    ) -> None:
        if transaction_repository is None or wallet_repository is None:
            registry = get_repository_registry()
            transaction_repository = transaction_repository or registry.transaction_repository
            wallet_repository = wallet_repository or registry.wallet_repository

        self._transaction_repository = transaction_repository
        self._wallet_repository = wallet_repository

    async def handle(self, query: GetFallbackTransactionQuery) -> TransactionPlainDTO:
        transaction = await self._transaction_repository.get_user_transaction_by_id(
            user_id=query.user_id,
            transaction_id=query.transaction_id,
        )

        if transaction.cancels_other is not None or transaction.adjusts_other is not None:
            raise FallbackTransactionNotVisibleError(
                f"Transaction {query.transaction_id} is a ledger effect, not a transaction"
            )

        self_cancellation = await self._transaction_repository.get_cancelling_transaction(
            query.transaction_id
        )
        if self_cancellation is not None:
            raise FallbackTransactionNotVisibleError(
                f"Transaction {query.transaction_id} has been cancelled"
            )

        adjustment = await self._transaction_repository.get_adjusting_transaction(
            query.transaction_id
        )
        effective_amount = transaction.amount + (
            adjustment.amount if adjustment is not None else Decimal("0")
        )
        currency_code = await self._wallet_currency(
            transaction.source_wallet_id,
            query.user_id,
        )

        return TransactionPlainDTO(
            id=UUID(transaction.unique_id),
            amount=effective_amount,
            currency_code=currency_code,
            source_wallet_id=str(transaction.source_wallet_id),
            created_at=transaction.created_at,
            cancels_other=transaction.cancels_other,
            adjusts_other=transaction.adjusts_other,
        )

    async def _wallet_currency(self, wallet_id: UUID, user_id: int) -> str:
        try:
            wallet = await self._wallet_repository.get_user_wallet_by_id(wallet_id, user_id)
        except Exception:
            return ""

        return wallet.currency_code
