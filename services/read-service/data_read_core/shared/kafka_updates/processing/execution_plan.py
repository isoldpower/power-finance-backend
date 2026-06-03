import asyncio

from ..types import EventMessage
from .sync_process_group import SyncProcessGroup


class ExecutionPlan:
    """The full processing plan for one event type: a list of
    SyncProcessGroups run concurrently with each other."""

    def __init__(self, groups: list[SyncProcessGroup]) -> None:
        if not groups:
            raise ValueError("ExecutionPlan requires at least one group")
        self._groups = list(groups)

    async def __call__(self, event: EventMessage) -> None:
        results = await asyncio.gather(
            *(group.run(event) for group in self._groups),
            return_exceptions=True,
        )
        errors = [result for result in results if isinstance(result, BaseException)]

        if not errors:
            return
        if len(errors) == 1:
            raise errors[0]
        raise BaseExceptionGroup("ExecutionPlan: one or more groups failed", errors)
