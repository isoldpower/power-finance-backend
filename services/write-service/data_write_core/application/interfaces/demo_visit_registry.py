from abc import ABC, abstractmethod
from datetime import datetime


class DemoVisitRegistry(ABC):
    @abstractmethod
    async def claim_active_visit(
        self,
        client_address: str,
        candidate_identifier: str,
        hold_until: datetime,
    ) -> str:
        raise NotImplementedError()

    @abstractmethod
    async def replace_active_visit(
        self,
        client_address: str,
        identifier: str,
        hold_until: datetime,
    ) -> None:
        raise NotImplementedError()
