from abc import ABC, abstractmethod

from ...dtos import QuotaDecisionDTO


class QuotaRepository(ABC):
    @abstractmethod
    async def consume_message(self, external_id: str) -> QuotaDecisionDTO: ...

    @abstractmethod
    async def refund_message(self, external_id: str) -> QuotaDecisionDTO: ...
