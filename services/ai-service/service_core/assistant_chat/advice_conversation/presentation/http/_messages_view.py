from fastapi import Request

from service_core.shared.http_contract import ok
from service_core.shared.pagination import (
    OrderSettings,
    build_page,
    decode_cursor,
    decode_message_anchor,
    query_fingerprint,
    resolve_limit,
)

from ...application import MessageRepository, dtos_to_conversation_messages
from ...domain.entities import ConversationMessage
from ...infrastructure import require_gateway_user
from ..message_view import present_messages


async def list_messages(
    request: Request,
    messages: MessageRepository,
    limit: str | None,
    cursor: str | None,
) -> dict:
    external_id = require_gateway_user(request)
    page_size = resolve_limit(limit)

    fingerprint = query_fingerprint(OrderSettings.MESSAGE_FEED)
    decoded = decode_cursor(cursor, fingerprint) if cursor else None
    anchor = decode_message_anchor(decoded) if decoded else None

    rows = dtos_to_conversation_messages(
        await messages.page(
            external_id,
            limit=page_size,
            anchor=anchor,
            backwards=decoded.backwards if decoded else False,
        )
    )
    total = await messages.count(external_id)

    page = build_page(
        rows,
        total=total,
        limit=page_size,
        fingerprint=fingerprint,
        key_of=_feed_key,
        cursor=decoded,
    )

    return ok(present_messages(page.items), page.meta())


async def clear_messages(request: Request, messages: MessageRepository) -> dict:
    deleted = await messages.clear(require_gateway_user(request))

    return ok({"deleted": deleted})


def _feed_key(message: ConversationMessage) -> tuple:
    return message.created_at, message.id
