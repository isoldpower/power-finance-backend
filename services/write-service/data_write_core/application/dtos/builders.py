from decimal import Decimal
from uuid import UUID

from data_write_core.domain.entities import TransactionEntity, WalletEntity

from .transaction_dto import TransactionDTO, TransactionPlainDTO
from .wallet_dto import WalletDTO


def wallet_to_dto(wallet: WalletEntity, balance_amount: Decimal | None = None) -> WalletDTO:
    return WalletDTO(
        id=UUID(wallet.unique_id),
        user_id=int(wallet.user_id),
        name=wallet.title,
        balance_amount=balance_amount if balance_amount is not None else Decimal("0"),
        currency=wallet.currency_code,
        created_at=wallet.created_at,
        updated_at=wallet.updated_at,
    )


def transaction_to_dto(
    transaction: TransactionEntity,
    source_wallet: WalletDTO,
) -> TransactionDTO:
    return TransactionDTO(
        id=UUID(transaction.unique_id),
        amount=transaction.amount,
        source_wallet=source_wallet,
        currency_code=source_wallet.currency,
        created_at=transaction.created_at,
        cancels_other=transaction.cancels_other,
        adjusts_other=transaction.adjusts_other,
    )


def transaction_to_plain_dto(
    transaction: TransactionEntity,
    source_wallet: WalletDTO,
) -> TransactionPlainDTO:
    return TransactionPlainDTO(
        id=UUID(transaction.unique_id),
        amount=transaction.amount,
        source_wallet_id=str(source_wallet.id),
        currency_code=source_wallet.currency,
        created_at=transaction.created_at,
        cancels_other=transaction.cancels_other,
        adjusts_other=transaction.adjusts_other,
    )
