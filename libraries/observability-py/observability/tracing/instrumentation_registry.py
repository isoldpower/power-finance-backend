from typing import Protocol, runtime_checkable

from ..logging import get_observability_logger


@runtime_checkable
class InstrumentationActivator(Protocol):
    @property
    def instrumentation_name(self) -> str: ...

    def activate(self) -> None: ...


class InstrumentationRegistry:
    def __init__(self) -> None:
        self._activators: list[InstrumentationActivator] = []
        self._activated_names: set[str] = set()
        self._logger = get_observability_logger()

    def register(self, activator: InstrumentationActivator) -> None:
        self._activators.append(activator)

    def activate_all(self) -> None:
        for activator in self._activators:
            self._activate_one(activator)

    def activated_instrumentation_names(self) -> list[str]:
        return sorted(self._activated_names)

    def _activate_one(self, activator: InstrumentationActivator) -> None:
        instrumentation_name = activator.instrumentation_name
        if instrumentation_name in self._activated_names:
            return

        try:
            activator.activate()
        except ImportError:
            self._logger.warning(
                "instrumentation package missing, skipped: %s",
                instrumentation_name,
            )
            return
        except Exception:
            self._logger.exception(
                "instrumentation activation failed: %s",
                instrumentation_name,
            )
            return

        self._activated_names.add(instrumentation_name)
