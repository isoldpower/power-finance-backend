from decimal import Decimal
from uuid import UUID

from ..exceptions import ConflictingTransactionDataError


class TransactionData:
    source_wallet_id: UUID
    amount: Decimal
    cancels_other: UUID | None
    adjusts_other: UUID | None

    def __init__(
        self,
        source_wallet_id: UUID,
        amount: Decimal,
        cancels_other: UUID | None,
        adjusts_other: UUID | None,
    ) -> None:
        if cancels_other is not None and adjusts_other is not None:
            raise ConflictingTransactionDataError()

        self.source_wallet_id = source_wallet_id
        self.amount = amount
        self.cancels_other = cancels_other
        self.adjusts_other = adjusts_other
