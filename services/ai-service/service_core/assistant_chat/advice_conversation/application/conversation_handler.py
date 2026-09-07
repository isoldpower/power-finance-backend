from collections.abc import AsyncIterator
from datetime import UTC, datetime
from uuid import uuid4

from service_core.shared.logging import get_service_logger

from ..config import (
    GENERATION_FAILED,
    GENERATION_FAILED_MESSAGE,
    PROMPT_FIELD,
)
from ..domain.entities import (
    ConversationMessage,
    MessageRole,
    MessageStatus,
    ResourceReference,
    accepted_frame,
    delta_frame,
    error_frame,
    message_frame,
)
from ..presentation.message_view import present_message
from .contracts import (
    ClientDisconnectedError,
    ConnectionContext,
    MessageHandler,
    MessageRepository,
    ReferenceExtractor,
    ReplyGenerator,
)
from .dtos import (
    conversation_message_to_dto,
    dtos_to_resource_references,
    resource_references_to_dtos,
)

logger = get_service_logger("assistant_chat")


class ConversationHandler(MessageHandler):
    def __init__(
        self,
        messages: MessageRepository,
        generator: ReplyGenerator,
        references: ReferenceExtractor,
    ) -> None:
        self._messages = messages
        self._generator = generator
        self._references = references

    async def is_responsible(self, message: dict, context: ConnectionContext) -> bool:
        return isinstance(message.get(PROMPT_FIELD), str)

    async def handle(
        self,
        message: dict,
        context: ConnectionContext,
    ) -> AsyncIterator[dict]:
        prompt = message[PROMPT_FIELD]
        question, answer = await self._open_turn(prompt, context)

        yield accepted_frame(
            user_message_id=question.id,
            message_id=answer.id,
        )

        produced = ""
        try:
            async for increment in self._generator.generate(prompt, context):
                produced += increment
                yield delta_frame(increment)
        except ClientDisconnectedError:
            await self._settle(answer, produced, context, MessageStatus.FAILED)
            raise
        except Exception:
            logger.exception("assistant reply generation failed")
            await self._settle(answer, produced, context, MessageStatus.FAILED)
            yield error_frame(GENERATION_FAILED, GENERATION_FAILED_MESSAGE, answer.id)
            return

        settled = await self._settle(answer, produced, context, MessageStatus.COMPLETE)
        yield message_frame(present_message(settled))

    async def _open_turn(
        self,
        prompt: str,
        context: ConnectionContext,
    ) -> tuple[ConversationMessage, ConversationMessage]:
        now = datetime.now(UTC)
        question = ConversationMessage(
            id=uuid4(),
            role=MessageRole.USER,
            status=MessageStatus.COMPLETE,
            text=prompt,
            created_at=now,
        )
        answer = ConversationMessage(
            id=uuid4(),
            role=MessageRole.ASSISTANT,
            status=MessageStatus.STREAMING,
            text="",
            created_at=now,
        )

        await self._messages.append(
            context.external_id,
            conversation_message_to_dto(question),
        )
        await self._messages.append(
            context.external_id,
            conversation_message_to_dto(answer),
        )

        return question, answer

    async def _settle(
        self,
        answer: ConversationMessage,
        text: str,
        context: ConnectionContext,
        status: MessageStatus,
    ) -> ConversationMessage:
        references = await self._extract(text, context)
        await self._messages.settle(
            answer.id,
            str(status),
            text,
            resource_references_to_dtos(references),
        )

        return ConversationMessage(
            id=answer.id,
            role=answer.role,
            status=status,
            text=text,
            created_at=answer.created_at,
            refs=references,
        )

    async def _extract(
        self,
        text: str,
        context: ConnectionContext,
    ) -> tuple[ResourceReference, ...]:
        try:
            return dtos_to_resource_references(await self._references.extract(text, context))
        except Exception:
            logger.exception("reference extraction failed; storing the reply without refs")

            return ()
