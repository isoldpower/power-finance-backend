from finances.application.dtos import WalletDTO
from finances.domain.entities.wallet import Wallet


def wallet_to_dto(wallet: Wallet) -> WalletDTO:
    return WalletDTO(
        id=wallet.id,
        user_id=wallet.user_id,
        name=wallet.name,
        balance_amount=wallet.balance.amount,
        currency=wallet.balance.currency_code,
        credit=wallet.credit,
        created_at=wallet.created_at,
        updated_at=wallet.updated_at,
    )