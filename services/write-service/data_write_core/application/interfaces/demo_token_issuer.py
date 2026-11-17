from abc import ABC, abstractmethod
from datetime import datetime
from typing import NamedTuple


class IssuedDemoToken(NamedTuple):
    token: str
    expires_at: datetime


class DemoTokenIssuer(ABC):
    @abstractmethod
    def issue(self, external_id: str, not_after: datetime | None = None) -> IssuedDemoToken:
        raise NotImplementedError()
