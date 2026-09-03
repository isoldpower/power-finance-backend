from fastapi import Request

from service_core.shared.http_contract import ok
from service_core.shared.pagination import (
    MESSAGE_FEED_ORDER,
    build_page,
    decode_cursor,
    decode_message_anchor,
    query_fingerprint,
    resolve_limit,
)

from ..contracts import ConversationMessage
from ..infrastructure import require_gateway_user
from ..message_view import present_messages
from ..repositories import MessageRepository


async def list_messages(
    request: Request,
    messages: MessageRepository,
    limit: str | None,
    cursor: str | None,
) -> dict:
    """The conversation, newest first.

    A chat feed reads oldest-first, so the CLIENT reverses each page for
    display. The API does not invert its ordering for one endpoint: paging
    backwards through a conversation means fetching newest-first, and a feed
    that paginated oldest-first would have to know its own length before it
    could start.
    """

    external_id = require_gateway_user(request)
    page_size = resolve_limit(limit)

    fingerprint = query_fingerprint(MESSAGE_FEED_ORDER)
    decoded = decode_cursor(cursor, fingerprint) if cursor else None
    anchor = decode_message_anchor(decoded) if decoded else None

    rows = await messages.page(
        external_id,
        limit=page_size,
        anchor=anchor,
        backwards=decoded.backwards if decoded else False,
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
    """A HARD delete of the whole conversation.

    There is no per-message deletion: the assistant reads the history as
    context, and a half-deleted exchange reads as a non-sequitur.
    """

    deleted = await messages.clear(require_gateway_user(request))

    return ok({"deleted": deleted})


def _feed_key(message: ConversationMessage) -> tuple:
    return (message.created_at, message.id)
