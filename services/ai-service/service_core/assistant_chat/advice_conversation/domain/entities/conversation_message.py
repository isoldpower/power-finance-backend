from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from .resource_reference import ResourceReference


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class MessageStatus(StrEnum):
    STREAMING = "streaming"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    id: UUID
    role: MessageRole
    status: MessageStatus
    text: str
    created_at: datetime
    refs: tuple[ResourceReference, ...] = field(default_factory=tuple)
