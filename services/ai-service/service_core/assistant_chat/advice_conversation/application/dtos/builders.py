from ...domain.entities import (
    ConversationMessage,
    MessageRole,
    MessageStatus,
    ResourceReference,
)
from .conversation_message_dto import ConversationMessageDTO
from .resource_reference_dto import ResourceReferenceDTO


def resource_reference_to_dto(reference: ResourceReference) -> ResourceReferenceDTO:
    return ResourceReferenceDTO(type=reference.type, id=reference.id)


def dto_to_resource_reference(dto: ResourceReferenceDTO) -> ResourceReference:
    return ResourceReference(type=dto.type, id=dto.id)


def resource_references_to_dtos(
    references: tuple[ResourceReference, ...],
) -> tuple[ResourceReferenceDTO, ...]:
    return tuple(resource_reference_to_dto(reference) for reference in references)


def dtos_to_resource_references(
    dtos: tuple[ResourceReferenceDTO, ...],
) -> tuple[ResourceReference, ...]:
    return tuple(dto_to_resource_reference(dto) for dto in dtos)


def conversation_message_to_dto(message: ConversationMessage) -> ConversationMessageDTO:
    return ConversationMessageDTO(
        id=message.id,
        role=str(message.role),
        status=str(message.status),
        text=message.text,
        created_at=message.created_at,
        refs=resource_references_to_dtos(message.refs),
    )


def dto_to_conversation_message(dto: ConversationMessageDTO) -> ConversationMessage:
    return ConversationMessage(
        id=dto.id,
        role=MessageRole(dto.role),
        status=MessageStatus(dto.status),
        text=dto.text,
        created_at=dto.created_at,
        refs=dtos_to_resource_references(dto.refs),
    )


def dtos_to_conversation_messages(
    dtos: list[ConversationMessageDTO],
) -> list[ConversationMessage]:
    return [dto_to_conversation_message(dto) for dto in dtos]
