from collections.abc import Sequence

from saga_pattern_py import SagaStep

from data_write_core.domain.entities import MoneyFlowEntity
from data_write_core.domain.value_objects import OutboxEntry
from data_write_core.infrastructure.outbox_saga import (
    FinalizedSagaCoordinator,
    ImmudbMoneyFlowStep,
    PostgresOutboxEmissionStep,
    PostgresWriteStep,
)

from ...interfaces import MoneyFlowRepository, OutboxRepository


async def run_transaction_saga(
    postgres_steps: Sequence[PostgresWriteStep],
    flows: Sequence[MoneyFlowEntity],
    entries: Sequence[OutboxEntry],
    money_flow_repository: MoneyFlowRepository,
    outbox_repository: OutboxRepository,
) -> int:
    steps: list[SagaStep] = list(postgres_steps)
    steps.extend(
        ImmudbMoneyFlowStep(
            repository=money_flow_repository,
            transaction=flow,
        )
        for flow in flows
    )

    coordinator = FinalizedSagaCoordinator(
        transaction_steps=steps,
        final_step=PostgresOutboxEmissionStep(
            outbox_repository=outbox_repository,
            entries=list(entries),
        ),
    )

    return await coordinator.run_transaction()
