from decimal import Decimal
from uuid import UUID

from django.utils.dateparse import parse_datetime

from data_write_core.domain.entities import MoneyFlowEntity
from data_write_core.domain.value_objects import MoneyFlowData


class MoneyFlowMapper:
    @staticmethod
    def to_domain(row: dict) -> MoneyFlowEntity:
        raw_cancels = row.get("cancels_other")
        raw_adjusts = row.get("adjusts_other")

        return MoneyFlowEntity.from_persistence(
            id=UUID(row["id"]),
            user_id=int(row["user_id"]),
            created_at=parse_datetime(row["created_at"]),
            data=MoneyFlowData(
                transaction_id=UUID(row.get("transaction_id") or row["id"]),
                container_id=UUID(row["source_wallet_id"]),
                amount=Decimal(row["amount"]),
                cancels_other=(UUID(raw_cancels) if raw_cancels else None),
                adjusts_other=(UUID(raw_adjusts) if raw_adjusts else None),
            ),
        )
