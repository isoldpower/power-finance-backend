from abc import ABC, abstractmethod
from enum import Enum


class ProbeStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"


class DatabaseHealth(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """How this dependency is named in the probe's `checks` map."""

        raise NotImplementedError()

    @abstractmethod
    async def is_reachable(self) -> bool:
        """False when the store is down. Raising means the check itself broke."""

        raise NotImplementedError()


class DatabaseMigrations(ABC):
    @abstractmethod
    async def pending(self) -> tuple[str, ...]:
        """The revisions this code knows about that the database has not applied."""

        raise NotImplementedError()
