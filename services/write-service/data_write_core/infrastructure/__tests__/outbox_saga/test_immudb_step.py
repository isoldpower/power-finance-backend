"""ImmudbTransactionStep: forward writes the txn; compensate writes its inverse."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest import IsolatedAsyncioTestCase
from uuid import UUID, uuid4

from data_write_core.domain.entities import TransactionEntity
from data_write_core.domain.value_objects import TransactionData
from data_write_core.infrastructure.outbox_saga import ImmudbTransactionStep


class _RecordingTransactionRepo:
    def __init__(self) -> None:
        self.created: list[TransactionEntity] = []

    async def create_transaction(self, txn: TransactionEntity) -> None:
        self.created.append(txn)


def _txn(amount: Decimal = Decimal("10")) -> TransactionEntity:
    return TransactionEntity.from_persistence(
        id=uuid4(),
        user_id=1,
        created_at=datetime(2026, 1, 1),
        data=TransactionData(
            source_wallet_id=uuid4(),
            amount=amount,
            cancels_other=None,
            adjusts_other=None,
        ),
    )


class ImmudbTransactionStepTests(IsolatedAsyncioTestCase):
    async def test_forward_calls_repository_with_provided_transaction(self) -> None:
        repo = _RecordingTransactionRepo()
        txn = _txn()
        step = ImmudbTransactionStep(repository=repo, transaction=txn)  # type: ignore[arg-type]

        await step.forward()

        self.assertEqual(len(repo.created), 1)
        self.assertIs(repo.created[0], txn)

    async def test_compensate_writes_an_inverse_with_negated_amount(self) -> None:
        repo = _RecordingTransactionRepo()
        original = _txn(amount=Decimal("25"))
        step = ImmudbTransactionStep(repository=repo, transaction=original)  # type: ignore[arg-type]

        await step.compensate()

        self.assertEqual(len(repo.created), 1)
        inverse = repo.created[0]
        self.assertEqual(inverse.amount, Decimal("-25"))
        self.assertEqual(inverse.cancels_other, UUID(original.unique_id))

    async def test_compensate_does_not_replay_forward(self) -> None:
        repo = _RecordingTransactionRepo()
        original = _txn()
        step = ImmudbTransactionStep(repository=repo, transaction=original)  # type: ignore[arg-type]

        await step.compensate()

        self.assertNotIn(original, repo.created)

    async def test_forward_then_compensate_writes_two_rows(self) -> None:
        repo = _RecordingTransactionRepo()
        txn = _txn(amount=Decimal("5"))
        step = ImmudbTransactionStep(repository=repo, transaction=txn)  # type: ignore[arg-type]

        await step.forward()
        await step.compensate()

        self.assertEqual(len(repo.created), 2)
        self.assertEqual(repo.created[0].amount, Decimal("5"))
        self.assertEqual(repo.created[1].amount, Decimal("-5"))
