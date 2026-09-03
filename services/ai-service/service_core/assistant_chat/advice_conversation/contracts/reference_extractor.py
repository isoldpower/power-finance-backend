from abc import ABC, abstractmethod

from .connection_context import ConnectionContext
from .resource_reference import ResourceReference


class ReferenceExtractor(ABC):
    @abstractmethod
    async def extract(
        self,
        text: str,
        context: ConnectionContext,
    ) -> tuple[ResourceReference, ...]: ...
