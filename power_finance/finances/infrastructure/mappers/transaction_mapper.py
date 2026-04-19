from decimal import Decimal
from uuid import UUID
from django.utils.dateparse import parse_datetime

from finances.domain.entities import Transaction


class TransactionMapper:
    @staticmethod
    def to_domain(model: dict) -> Transaction:
        raw_cancels = model.get('cancels_other')
        raw_adjusts = model.get('adjusts_other')
        return Transaction.from_persistence(
            transaction_id=UUID(model.get('id')),
            user_id=int(model.get('user_id')),
            wallet_id=UUID(model.get('source_wallet_id')),
            amount=Decimal(model.get('amount')),
            created_at=parse_datetime(model.get('created_at')),
            cancels_other=UUID(raw_cancels) if raw_cancels else None,
            adjusts_other=UUID(raw_adjusts) if raw_adjusts else None,
        )