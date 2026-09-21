from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResourceReferenceDTO:
    type: str
    id: UUID
