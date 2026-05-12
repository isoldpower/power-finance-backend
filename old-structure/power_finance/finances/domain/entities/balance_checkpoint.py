from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from django.utils import timezone


@dataclass(frozen=True)
class BalanceCheckpoint:
    wallet_id: UUID
    balance: Decimal
    currency: str
    settled_at: str
    last_tx_id: UUID | None

    @classmethod
    def create(cls, wallet) -> 'BalanceCheckpoint':
        last_tx_id = wallet.unsettled_transactions[-1].id if wallet.unsettled_transactions else None

        return cls(
            wallet_id=wallet.id,
            balance=wallet.balance,
            currency=wallet.currency_code,
            settled_at=timezone.now().isoformat(),
            last_tx_id=last_tx_id,
        )
