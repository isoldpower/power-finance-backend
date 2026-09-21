from uuid import UUID

from service_core.shared.db_connection import AssistantMessageModel

from ....application.dtos import ConversationMessageDTO, ResourceReferenceDTO


class AssistantMessageMapper:
    @staticmethod
    def to_dto(model: AssistantMessageModel) -> ConversationMessageDTO:
        return ConversationMessageDTO(
            id=model.id,
            role=model.role,
            status=model.status,
            text=model.text,
            created_at=model.created_at,
            refs=tuple(
                ResourceReferenceDTO(type=reference["type"], id=UUID(reference["id"]))
                for reference in model.refs or []
            ),
        )

    @staticmethod
    def to_model(external_id: str, dto: ConversationMessageDTO) -> AssistantMessageModel:
        return AssistantMessageModel(
            id=dto.id,
            external_id=external_id,
            role=dto.role,
            status=dto.status,
            text=dto.text,
            refs=AssistantMessageMapper.refs_to_columns(dto.refs),
            created_at=dto.created_at,
        )

    @staticmethod
    def refs_to_columns(refs: tuple[ResourceReferenceDTO, ...]) -> list[dict]:
        return [{"type": reference.type, "id": str(reference.id)} for reference in refs]
