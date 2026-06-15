"""TransactionData: a transaction can be a cancellation OR an adjustment, not
both — pins the only validation it enforces."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from django.test import SimpleTestCase

from data_write_core.domain.exceptions import ConflictingTransactionDataError
from data_write_core.domain.value_objects.transaction_data import TransactionData


class TransactionDataTests(SimpleTestCase):
    def test_plain_transaction_stores_all_fields_verbatim(self) -> None:
        wallet_id = uuid4()
        data = TransactionData(
            source_wallet_id=wallet_id,
            amount=Decimal("42.10"),
            cancels_other=None,
            adjusts_other=None,
        )

        self.assertEqual(data.source_wallet_id, wallet_id)
        self.assertEqual(data.amount, Decimal("42.10"))
        self.assertIsNone(data.cancels_other)
        self.assertIsNone(data.adjusts_other)

    def test_cancellation_transaction_is_valid(self) -> None:
        cancelled_id = uuid4()
        data = TransactionData(
            source_wallet_id=uuid4(),
            amount=Decimal("-10"),
            cancels_other=cancelled_id,
            adjusts_other=None,
        )

        self.assertEqual(data.cancels_other, cancelled_id)
        self.assertIsNone(data.adjusts_other)

    def test_adjustment_transaction_is_valid(self) -> None:
        adjusted_id = uuid4()
        data = TransactionData(
            source_wallet_id=uuid4(),
            amount=Decimal("5"),
            cancels_other=None,
            adjusts_other=adjusted_id,
        )

        self.assertEqual(data.adjusts_other, adjusted_id)
        self.assertIsNone(data.cancels_other)

    def test_simultaneous_cancellation_and_adjustment_is_rejected(self) -> None:
        with self.assertRaises(ConflictingTransactionDataError):
            TransactionData(
                source_wallet_id=uuid4(),
                amount=Decimal("1"),
                cancels_other=uuid4(),
                adjusts_other=uuid4(),
            )
