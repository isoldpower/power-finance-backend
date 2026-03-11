from finances.domain.entities.wallet import Wallet
from finances.domain.value_objects import Money
from finances.infrastructure.orm.wallet import WalletModel

from .currency_mapper import CurrencyMapper


class WalletMapper:
    WALLET_EDITABLE_MAP = [
        ('user_id', 'user_id'),
        ('name', 'name'),
        ('balance_amount', 'balance.amount'),
        ('currency_id', 'balance.currency_code'),
        ('credit', 'credit'),
        ('deleted_at', 'deleted_at'),
    ]

    @staticmethod
    def _resolve_attr(obj, path: str):
        current = obj
        for part in path.split("."):
            current = getattr(current, part)
        return current

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
    def update_model(model: WalletModel, entity: Wallet) -> WalletModel:
        for model_field, entity_field in WalletMapper.WALLET_EDITABLE_MAP:
            entity_value = WalletMapper._resolve_attr(entity, entity_field)
            model_value = getattr(model, model_field)

            if model_value != entity_value:
                setattr(model, model_field, entity_value)

        return model

    @staticmethod
    def get_changed_fields(model: WalletModel, entity: Wallet) -> list[str]:
        changed_fields = ["updated_at"]
        for model_field, entity_field in WalletMapper.WALLET_EDITABLE_MAP:
            entity_value = WalletMapper._resolve_attr(entity, entity_field)
            model_value = getattr(model, model_field)

            if model_value != entity_value:
                changed_fields.append(model_field)

        return changed_fields