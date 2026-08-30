from ..types import EventMessage, Handler
from .health_probe import HealthProbe
from .logger_shortcuts import warn_projection_unavailable


class HealthGuardedHandler:
    """Wraps a projection so a downstream outage blocks consumption instead of
    losing the event."""

    def __init__(
        self,
        handler: Handler,
        health_probe: HealthProbe,
        guarded_errors: tuple[type[BaseException], ...],
    ) -> None:
        self._handler = handler
        self._health_probe = health_probe
        self._guarded_errors = guarded_errors

    async def __call__(self, event: EventMessage) -> None:
        while True:
            try:
                await self._handler(event)

                return
            except self._guarded_errors as error:
                warn_projection_unavailable(self._health_probe.name, event.event_id, error)
                await self._health_probe.wait_until_healthy()
