"""@idempotent — async DRF view-method decorator.

Usage:

    class TransactionListView(APIView):
        @idempotent(required=True)        # money-moving: header mandatory
        async def post(self, request, ...):
            ...

    class WalletListView(APIView):
        @idempotent(required=False)       # optional dedup on wallet ops
        async def post(self, request, ...):
            ...

The decorator owns the workflow; the view stays oblivious. Successful
responses (2xx/3xx) are cached for the configured TTL. Client-error and
server-error responses release the lock immediately, so the client can fix
the payload and retry with the same key.
"""

from __future__ import annotations

import functools
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from rest_framework.response import Response

from .exceptions import (
    IdempotencyInFlight,
    IdempotencyKeyRequired,
    IdempotencyKeyReused,
    IdempotencyUnavailable,
)
from .request_hash import fingerprint
from .store import (
    Acquired,
    AlreadyCompleted,
    InProgress,
    Mismatch,
    RedisIdempotencyStore,
    StoredResponse,
    StoreUnavailable,
)

logger = logging.getLogger(__name__)

IDEMPOTENCY_HEADER = "Idempotency-Key"
_REPLAY_HEADER = "Idempotent-Replayed"

# Module-level store handle; populated by the Django AppConfig at process
# start (or lazily on first request in tests). Tests inject a fake by
# calling `set_store()` directly.
_store: RedisIdempotencyStore | None = None


def set_store(store: RedisIdempotencyStore | None) -> None:
    global _store
    _store = store


def get_store() -> RedisIdempotencyStore | None:
    return _store


AsyncViewMethod = Callable[..., Awaitable[Response]]


def idempotent(*, required: bool) -> Callable[[AsyncViewMethod], AsyncViewMethod]:
    """Wrap an async DRF view method with Idempotency-Key dedup.

    `required=True` — missing header returns 400; Redis outage returns 503.
    `required=False` — missing header skips dedup; Redis outage skips dedup
    with a logged warning.
    """

    def decorator(func: AsyncViewMethod) -> AsyncViewMethod:
        @functools.wraps(func)
        async def wrapper(view_self, request, *args, **kwargs) -> Response:
            key = _extract_key(request)

            if key is None:
                if required:
                    raise IdempotencyKeyRequired()
                return await func(view_self, request, *args, **kwargs)

            store = get_store()
            if store is None:
                return await _handle_no_store(required, func, view_self, request, args, kwargs)

            user_id = _user_id(request)
            request_hash = fingerprint(request.method, request.path, request.data)

            try:
                outcome = await store.try_acquire(user_id, key, request_hash)
            except StoreUnavailable as exc:
                logger.warning(
                    "idempotency.store_unavailable on acquire: %s (required=%s)",
                    exc,
                    required,
                )
                if required:
                    raise IdempotencyUnavailable() from exc
                return await func(view_self, request, *args, **kwargs)

            if isinstance(outcome, AlreadyCompleted):
                return _rebuild_response(outcome.response)
            if isinstance(outcome, InProgress):
                raise IdempotencyInFlight()
            if isinstance(outcome, Mismatch):
                raise IdempotencyKeyReused()
            assert isinstance(outcome, Acquired)

            try:
                response = await func(view_self, request, *args, **kwargs)
            except BaseException:
                await store.release_lock(user_id, key)
                raise

            if 200 <= response.status_code < 400:
                try:
                    await store.store_response(
                        user_id,
                        key,
                        request_hash=request_hash,
                        status_code=response.status_code,
                        body=response.data,
                    )
                except StoreUnavailable as exc:
                    # Response is already shaped — don't fail the request just
                    # because we couldn't cache it. A retry will simply land
                    # twice, which is the pre-idempotency baseline.
                    logger.warning("idempotency.store_unavailable on store: %s", exc)
            else:
                await store.release_lock(user_id, key)

            return response

        return wrapper

    return decorator


def _extract_key(request) -> str | None:
    raw = request.headers.get(IDEMPOTENCY_HEADER)
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    # Cap to defend against pathological clients pushing huge keys into Redis.
    return raw[:255]


def _user_id(request) -> int | str:
    user = getattr(request, "user", None)
    user_id = getattr(user, "id", None)
    if user_id is None:
        # Anonymous shouldn't reach a write endpoint (auth runs first), but
        # bucket them together rather than crashing if it ever happens.
        return "anonymous"
    return user_id


def _rebuild_response(stored: StoredResponse) -> Response:
    response = Response(data=stored.body, status=stored.status_code)
    response[_REPLAY_HEADER] = "true"
    return response


async def _handle_no_store(
    required: bool,
    func: AsyncViewMethod,
    view_self: Any,
    request: Any,
    args: tuple,
    kwargs: dict,
) -> Response:
    if required:
        raise IdempotencyUnavailable()
    logger.warning("idempotency.store_not_configured — skipping dedup")
    return await func(view_self, request, *args, **kwargs)
