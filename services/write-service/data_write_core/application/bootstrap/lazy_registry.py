from typing import TypeVar, cast

from .state import RepositoryRegistry

TDependency = TypeVar("TDependency")


class LazyRegistry:
    def __init__(self) -> None:
        self._registry: RepositoryRegistry | None = None

    def __call__(self, given: TDependency | None, name: str) -> TDependency:
        if given is not None:
            return given

        return cast(
            TDependency,
            getattr(self._resolved(), name),
        )

    def _resolved(self) -> RepositoryRegistry:
        from . import get_repository_registry

        if self._registry is None:
            self._registry = get_repository_registry()

        return self._registry
