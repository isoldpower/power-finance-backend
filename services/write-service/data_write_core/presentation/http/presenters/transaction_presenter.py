from write_service.common.timestamps import to_iso

from data_write_core.application.dtos import (
    TransactionChainDTO,
    TransactionDTO,
    TransactionPlainDTO,
)
from data_write_core.application.money_scales import amount_at_scale, money_at_scale


class TransactionHttpPresenter:
    @staticmethod
    async def present_one(transaction: TransactionDTO) -> dict:
        return {
            "id": str(transaction.id),
            "name": transaction.name,
            "created_at": to_iso(transaction.created_at),
            "updated_at": to_iso(transaction.updated_at),
            "deleted_at": to_iso(transaction.deleted_at),
            "money": await money_at_scale(transaction.amount, transaction.currency_code),
            "type": str(transaction.transaction_type),
            "origin": str(transaction.origin),
            # The target renders a goal-funded transaction under `wallet` too:
            # clients treat the two interchangeably, and the container's kind is not
            # part of the transaction shape.
            "wallet": {
                "id": str(transaction.container.id),
                "name": transaction.container.name,
            },
            "category": transaction.category,
            "chain_id": str(transaction.chain_id) if transaction.chain_id else None,
        }

    @staticmethod
    async def present_previews(transactions: list[TransactionDTO]) -> list[dict]:
        return [
            await TransactionHttpPresenter.present_one(transaction) for transaction in transactions
        ]

    @staticmethod
    async def present_chain(chain: TransactionChainDTO) -> dict:
        return {
            "chain_id": str(chain.chain_id),
            "transactions": await TransactionHttpPresenter.present_previews(chain.transactions),
        }

    @staticmethod
    async def present_many(transactions: list[TransactionPlainDTO]) -> list[dict]:
        return [
            {
                "id": str(transaction.id),
                "amount": await amount_at_scale(
                    transaction.amount,
                    transaction.currency_code,
                ),
                "currency": transaction.currency_code,
                "wallet_id": str(transaction.container_id),
                "cancels_other": (
                    str(transaction.cancels_other) if transaction.cancels_other else None
                ),
                "adjusts_other": (
                    str(transaction.adjusts_other) if transaction.adjusts_other else None
                ),
                "created_at": to_iso(transaction.created_at),
                "updated_at": None,
                "deleted_at": None,
            }
            for transaction in transactions
        ]
