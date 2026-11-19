from abc import ABC, abstractmethod
from datetime import datetime
from typing import NamedTuple


class DemoVisit(NamedTuple):
    identifier: str
    nonce: str
    expires_at: datetime


class DemoVisitCodec(ABC):
    @abstractmethod
    def issue(self) -> DemoVisit:
        raise NotImplementedError()

    @abstractmethod
    def verify(self, identifier: str) -> DemoVisit | None:
        raise NotImplementedError()
