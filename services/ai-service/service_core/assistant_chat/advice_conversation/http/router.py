from collections.abc import Sequence

from fastapi import APIRouter, Query, Request, WebSocket
from sqlalchemy.ext.asyncio import async_sessionmaker

from service_core.shared.db_connection import get_session_factory
from service_core.shared.http_contract import ERROR_RESPONSES
from service_core.shared.logging import get_service_logger
from service_core.shared.pagination import DEFAULT_LIMIT, MAXIMUM_LIMIT

from ..contracts import MessageHandler, TerminationSignal
from ..generators import EchoReplyGenerator
from ..handlers import ConversationHandler
from ..infrastructure import SqlAlchemyMessageRepository
from ..message_router import MessageRouter
from ..references import ProjectedReferenceExtractor
from ..repositories import MessageRepository
from ..signals import NeverTerminates
from ._messages_view import clear_messages, list_messages
from ._schemas import ClearedConversationResponseSchema, MessageCollectionSchema
from ._wrappers import WrapperContext, chat_connection_wrapper

logger = get_service_logger("assistant_chat")


def build_message_repository(
    session_factory: async_sessionmaker | None = None,
) -> MessageRepository:
    return SqlAlchemyMessageRepository(session_factory or get_session_factory())


def build_chat_router(
    termination_signal: TerminationSignal | None = None,
    handlers: Sequence[MessageHandler] | None = None,
    messages: MessageRepository | None = None,
) -> APIRouter:
    connection_router = APIRouter(prefix="/chat")
    wrapper_context = WrapperContext(
        signal=termination_signal or NeverTerminates(),
        message_router=MessageRouter(
            handlers or [_default_handler(messages or build_message_repository())]
        ),
    )

    @connection_router.websocket("/advice")
    async def open_chat_connection(websocket: WebSocket) -> None:
        await chat_connection_wrapper(websocket, wrapper_context)

    return connection_router


def build_assistant_router(messages: MessageRepository | None = None) -> APIRouter:
    store = messages or build_message_repository()
    assistant_router = APIRouter(
        prefix="/assistant",
        tags=["assistant"],
        responses=ERROR_RESPONSES,
    )

    @assistant_router.get(
        "/messages",
        summary="Read the conversation",
        description=(
            "Newest first, like every collection here. A chat feed reads "
            "oldest-first, so the CLIENT reverses each page for display."
        ),
        response_model=MessageCollectionSchema,
    )
    async def get_messages(
        request: Request,
        limit: str | None = Query(
            None,
            description=(
                f"Page size. Defaults to {DEFAULT_LIMIT}, clamped to "
                f"1..{MAXIMUM_LIMIT} rather than refused."
            ),
        ),
        cursor: str | None = Query(
            None,
            description="Opaque cursor from a previous response's `meta.next_cursor`.",
        ),
    ) -> dict:
        return await list_messages(request, store, limit=limit, cursor=cursor)

    @assistant_router.delete(
        "/messages",
        summary="Clear the conversation",
        description=(
            "A HARD delete of the whole conversation. There is no per-message "
            "deletion: the assistant reads the history as context, and a "
            "half-deleted exchange reads as a non-sequitur."
        ),
        response_model=ClearedConversationResponseSchema,
    )
    async def delete_messages(request: Request) -> dict:
        return await clear_messages(request, store)

    return assistant_router


def _default_handler(messages: MessageRepository) -> MessageHandler:
    return ConversationHandler(
        messages=messages,
        generator=EchoReplyGenerator(),
        references=ProjectedReferenceExtractor(get_session_factory()),
    )
