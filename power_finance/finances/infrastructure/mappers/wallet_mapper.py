from finances.domain.entities import Wallet
from finances.domain.value_objects import Money
from finances.infrastructure.orm import WalletModel

from .currency_mapper import CurrencyMapper
from .update_mapper import UpdateMapper


class WalletMapper:
    WALLET_EDITABLE_MAP: list[tuple[str, str]] = [
        ('user_id', 'user_id'),
        ('name', 'name'),
        ('balance_amount', 'balance.amount'),
        ('currency_id', 'balance.currency_code'),
        ('credit', 'credit'),
        ('deleted_at', 'deleted_at'),
    ]

    @staticmethod
    def _get_initial_key(path: str):
        return path.split(".")[0]

    @staticmethod
    def to_domain(model: WalletModel) -> Wallet:
        mapped_currency = CurrencyMapper.to_domain(model.currency)

        return Wallet(
            id=model.id,
            user_id=model.user_id,
            name=model.name,
            balance=Money(
                amount=model.balance_amount,
                currency_code=mapped_currency.code,
            ),
            credit=model.credit,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )

    @staticmethod
    def update_model(model: WalletModel, entity: Wallet, replace: bool = False) -> WalletModel:
        return UpdateMapper[WalletModel, Wallet].update_model(
            model,
            entity,
            WalletMapper.WALLET_EDITABLE_MAP,
            replace
        )

    @staticmethod
    def get_changed_fields(model: WalletModel, entity: Wallet) -> list[str]:
        return UpdateMapper.get_changed_fields(
            model,
            entity,
            WalletMapper.WALLET_EDITABLE_MAP,
            updated_list=["updated_at"]
        )