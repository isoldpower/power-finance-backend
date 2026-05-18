from data_write_core.application.interfaces import EventBus

from ._gates import skip_without_infra
from .event_bus import initialize_event_bus
from .immudb import initialize_immudb
from .repositories import initialize_repositories
from .state import (
    ApplicationEnvironment,
    ApplicationState,
    ImmudbConnection,
    RepositoryRegistry,
)

_application: ApplicationState | None = None


@skip_without_infra
def bootstrap_application(environment: ApplicationEnvironment) -> ApplicationState:
    global _application
    if _application is not None and _application.initialized:
        return _application

    immudb_connection = initialize_immudb(environment)
    repository_registry = initialize_repositories(immudb_connection)
    event_bus = initialize_event_bus()

    _application = ApplicationState(
        initialized=True,
        immudb=immudb_connection,
        repository_registry=repository_registry,
        event_bus=event_bus,
    )
    return _application


def get_application_state() -> ApplicationState:
    if _application is None or not _application.initialized:
        raise RuntimeError("Application is not bootstrapped or still initializing")
    return _application


def get_repository_registry() -> RepositoryRegistry:
    return get_application_state().repository_registry


def get_event_bus() -> EventBus:
    return get_application_state().event_bus


__all__ = [
    "ApplicationEnvironment",
    "ApplicationState",
    "ImmudbConnection",
    "RepositoryRegistry",
    "bootstrap_application",
    "get_application_state",
    "get_event_bus",
    "get_repository_registry",
]
