from collections.abc import Awaitable, Callable

from saga_pattern_py import SagaStep

from data_write_core.application.db_utils import aatomic

PostgresAction = Callable[[], Awaitable[None]]


async def _noop() -> None:
    return


class PostgresWriteStep(SagaStep[None]):
    """Postgres business-write step for a SAGA."""

    def __init__(
        self,
        forward_action: PostgresAction,
        compensate_action: PostgresAction = _noop,
    ) -> None:
        self._forward_action = forward_action
        self._compensate_action = compensate_action

    async def forward(self) -> None:
        async with aatomic():
            await self._forward_action()

    async def compensate(self) -> None:
        async with aatomic():
            await self._compensate_action()
