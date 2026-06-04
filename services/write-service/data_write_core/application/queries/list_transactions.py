from dataclasses import dataclass
from uuid import UUID

from data_write_core.domain.services import collapse_ledger

from ..bootstrap import get_repository_registry
from ..dtos import TransactionPlainDTO
from ..interfaces import TransactionRepository, WalletRepository


@dataclass(frozen=True)
class ListFallbackTransactionsQuery:
    user_id: int
    limit: int
    offset: int


class ListFallbackTransactionsQueryHandler:
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

    async def handle(
        self, query: ListFallbackTransactionsQuery
    ) -> tuple[list[TransactionPlainDTO], int]:
        ledger = await self._transaction_repository.get_user_transactions(query.user_id)
        collapsed = collapse_ledger(ledger)
        collapsed.sort(key=lambda entry: entry.transaction.created_at, reverse=True)

        total = len(collapsed)
        page = collapsed[query.offset : query.offset + query.limit]

        currency_by_wallet = await self._currency_by_wallet(query.user_id)

        return [
            TransactionPlainDTO(
                id=UUID(entry.transaction.unique_id),
                amount=entry.effective_amount,
                currency_code=currency_by_wallet.get(str(entry.transaction.source_wallet_id), ""),
                source_wallet_id=str(entry.transaction.source_wallet_id),
                created_at=entry.transaction.created_at,
                cancels_other=entry.transaction.cancels_other,
                adjusts_other=entry.transaction.adjusts_other,
            )
            for entry in page
        ], total

    async def _currency_by_wallet(self, user_id: int) -> dict[str, str]:
        wallets = await self._wallet_repository.get_user_wallets(user_id)
        return {str(wallet.unique_id): wallet.currency_code for wallet in wallets}
