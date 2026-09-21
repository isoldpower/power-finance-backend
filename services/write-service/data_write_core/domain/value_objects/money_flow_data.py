from decimal import Decimal
from uuid import UUID

from ..exceptions import ConflictingMoneyFlowDataError


class MoneyFlowData:
    transaction_id: UUID
    container_id: UUID
    amount: Decimal
    cancels_other: UUID | None
    adjusts_other: UUID | None

    def __init__(
        self,
        transaction_id: UUID,
        container_id: UUID,
        amount: Decimal,
        cancels_other: UUID | None = None,
        adjusts_other: UUID | None = None,
    ) -> None:
        if cancels_other is not None and adjusts_other is not None:
            raise ConflictingMoneyFlowDataError()

        self.transaction_id = transaction_id
        self.container_id = container_id
        self.amount = amount
        self.cancels_other = cancels_other
        self.adjusts_other = adjusts_other
