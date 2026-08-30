from typing import Any

from saga_pattern_py import SagaCoordinator, SagaStep

from ..types import EventMessage
from .effect import Effect, EffectFn, as_effect


class _EffectSagaStep(SagaStep[None]):
    """Binds an Effect to a specific event so it satisfies the parameterless
    SagaStep contract the shared coordinator orchestrates."""

    def __init__(self, effect: Effect, event: EventMessage) -> None:
        self._effect = effect
        self._event = event

    @property
    def name(self) -> str:
        return self._effect.name

    async def forward(self) -> None:
        await self._effect.apply(self._event)

    async def compensate(self) -> None:
        await self._effect.compensate(self._event)


class SyncProcessGroup:
    """A group of effects that run sequentially for a single event. An atomic
    group runs through the shared SAGA coordinator, so a later failure
    compensates the effects already applied."""

    def __init__(
        self,
        effects: list[Effect | EffectFn],
        *,
        atomic: bool = False,
    ) -> None:
        if not effects:
            raise ValueError("SyncProcessGroup requires at least one effect")
        self._effects: list[Effect] = [as_effect(e) for e in effects]
        self._atomic = atomic

    async def run(self, event: EventMessage) -> None:
        if self._atomic:
            steps: list[SagaStep[Any]] = [
                _EffectSagaStep(effect, event) for effect in self._effects
            ]
            await SagaCoordinator(steps).run()
            return

        for effect in self._effects:
            await effect.apply(event)
