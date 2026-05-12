from abc import ABC, abstractmethod


class ServiceHealthChecker(ABC):
    """Port for any dependency that can report on its own reachability.
    Implementations live in `infrastructure/checkers/` and adapt concrete
    clients (Postgres, Redis, ImmuDB, Kafka, etc.) to a uniform async API.

    Returns a string: `ProbeStatus.OK.value` on success, or a human-readable
    error message on failure. Strings (rather than exceptions) keep
    `asyncio.gather(..., return_exceptions=True)` semantics simple and let
    presenters render diagnostics verbatim.
    """

    @abstractmethod
    async def health_status(self) -> str:
        raise NotImplementedError()
