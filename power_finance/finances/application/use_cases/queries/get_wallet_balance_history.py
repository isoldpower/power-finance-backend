from dataclasses import dataclass
from typing import Any
from uuid import UUID

from django.core.exceptions import ObjectDoesNotExist

from ...bootstrap import get_repository_registry
from ...interfaces import TransactionSelectorsCollection, WalletSelectorsCollection
from ...dtos import WalletBalanceHistoryItemDTO, WalletBalanceHistoryResultDTO


@dataclass(frozen=True)
class GetWalletBalanceHistoryQuery:
    user_id: int
    wallet_id: UUID


class GetWalletBalanceHistoryQueryHandler:
    transaction_selectors: TransactionSelectorsCollection
    wallet_selectors: WalletSelectorsCollection

    def __init__(
        self,
        transaction_selectors: TransactionSelectorsCollection | None = None,
        wallet_selectors: WalletSelectorsCollection | None = None,
    ) -> None:
        registry = get_repository_registry()
        self.transaction_selectors = transaction_selectors or registry.transaction_selectors
        self.wallet_selectors = wallet_selectors or registry.wallet_selectors

    def _record_transaction_history(self, wallet_id: UUID, transaction_rows: list[dict[str, Any]]):
        balance = 0.0
        history = []
        for transaction in transaction_rows:
            if transaction["send_wallet_id"] == wallet_id:
                balance -= float(transaction["send_amount"] or 0)

            if transaction["receive_wallet_id"] == wallet_id:
                balance += float(transaction["receive_amount"] or 0)

            history.append(WalletBalanceHistoryItemDTO(
                date=transaction["created_at"].date().isoformat(),
                balance=balance
            ))

        return history

    async def handle(self, query: GetWalletBalanceHistoryQuery) -> WalletBalanceHistoryResultDTO:
        try:
            await self.wallet_selectors.get_single_wallet(
                user_id=query.user_id,
                wallet_id=query.wallet_id
            )
        except ObjectDoesNotExist:
            raise ObjectDoesNotExist("Requested wallet's balance history not found.")

        transaction_rows = (await self.transaction_selectors.get_wallet_transactions(
            wallet_id=query.wallet_id
        ) or [])
        history = self._record_transaction_history(
            query.wallet_id,
            transaction_rows,
        )

        return WalletBalanceHistoryResultDTO(history=history)
