from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from .resource_reference_dto import ResourceReferenceDTO


@dataclass(frozen=True, slots=True)
class ConversationMessageDTO:
    id: UUID
    role: str
    status: str
    text: str
    created_at: datetime
    refs: tuple[ResourceReferenceDTO, ...] = field(default_factory=tuple)
