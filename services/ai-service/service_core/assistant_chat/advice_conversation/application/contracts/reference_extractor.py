from abc import ABC, abstractmethod

from ..dtos import ResourceReferenceDTO
from .connection_context import ConnectionContext


class ReferenceExtractor(ABC):
    @abstractmethod
    async def extract(
        self,
        text: str,
        context: ConnectionContext,
    ) -> tuple[ResourceReferenceDTO, ...]: ...
