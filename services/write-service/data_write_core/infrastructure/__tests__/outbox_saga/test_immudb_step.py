from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from unittest import IsolatedAsyncioTestCase
from uuid import UUID, uuid4

from data_write_core.domain.entities import MoneyFlowEntity
from data_write_core.domain.value_objects import MoneyFlowData
from data_write_core.infrastructure.outbox_saga import ImmudbMoneyFlowStep


class _RecordingTransactionRepository:
    def __init__(self) -> None:
        self.created: list[MoneyFlowEntity] = []

    async def create_transaction(self, money_flow: MoneyFlowEntity) -> None:
        self.created.append(money_flow)


def _money_flow(amount: Decimal = Decimal("10")) -> MoneyFlowEntity:
    return MoneyFlowEntity.from_persistence(
        id=uuid4(),
        user_id=1,
        created_at=datetime(2026, 1, 1),
        data=MoneyFlowData(
            transaction_id=uuid4(),
            container_id=uuid4(),
            amount=amount,
            cancels_other=None,
            adjusts_other=None,
        ),
    )


class ImmudbTransactionStepTests(IsolatedAsyncioTestCase):
    async def test_forward_calls_repository_with_provided_transaction(self) -> None:
        repository = _RecordingTransactionRepository()
        money_flow = _money_flow()
        step = ImmudbMoneyFlowStep(repository=repository, transaction=money_flow)  # type: ignore[arg-type]

        await step.forward()

        self.assertEqual(len(repository.created), 1)
        self.assertIs(repository.created[0], money_flow)

    async def test_compensate_writes_an_inverse_with_negated_amount(self) -> None:
        repository = _RecordingTransactionRepository()
        original = _money_flow(amount=Decimal("25"))
        step = ImmudbMoneyFlowStep(repository=repository, transaction=original)  # type: ignore[arg-type]

        await step.compensate()

        self.assertEqual(len(repository.created), 1)
        inverse = repository.created[0]
        self.assertEqual(inverse.amount, Decimal("-25"))
        self.assertEqual(inverse.cancels_other, UUID(original.unique_id))

    async def test_compensate_does_not_replay_forward(self) -> None:
        repository = _RecordingTransactionRepository()
        original = _money_flow()
        step = ImmudbMoneyFlowStep(repository=repository, transaction=original)  # type: ignore[arg-type]

        await step.compensate()

        self.assertNotIn(original, repository.created)

    async def test_forward_then_compensate_writes_two_rows(self) -> None:
        repository = _RecordingTransactionRepository()
        money_flow = _money_flow(amount=Decimal("5"))
        step = ImmudbMoneyFlowStep(repository=repository, transaction=money_flow)  # type: ignore[arg-type]

        await step.forward()
        await step.compensate()

        self.assertEqual(len(repository.created), 2)
        self.assertEqual(repository.created[0].amount, Decimal("5"))
        self.assertEqual(repository.created[1].amount, Decimal("-5"))
