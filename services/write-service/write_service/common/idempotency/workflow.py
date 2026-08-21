from collections.abc import Awaitable, Callable
from typing import Any

from rest_framework.response import Response

from .atomic_redis import (
    Acquired,
    AcquireResult,
    AlreadyCompleted,
    InProgress,
    Mismatch,
    RedisIdempotencyStore,
)
from .exceptions import (
    IdempotencyInFlight,
    IdempotencyKeyRequired,
    IdempotencyKeyReused,
    IdempotencyUnavailable,
    StoreUnavailable,
)
from .logger_shortcuts import (
    warn_store_not_configured,
    warn_store_unavailable_on_acquire,
    warn_store_unavailable_on_store,
)
from .replay_marker import mark_replay
from .replay_response import ReplayResponseBuilder
from .request_hash import fingerprint
from .request_inspector import RequestInspector

AsyncViewMethod = Callable[..., Awaitable[Response]]


def _is_successful_status(status_code: int) -> bool:
    return 200 <= status_code < 400


class IdempotencyWorkflow:
    def __init__(
        self,
        *,
        store: RedisIdempotencyStore | None,
        required: bool,
        view_callable: AsyncViewMethod,
        view_self: Any,
        request: Any,
        args: tuple,
        kwargs: dict,
    ) -> None:
        self._store = store
        self._required = required
        self._view_callable = view_callable
        self._view_self = view_self
        self._request = request
        self._args = args
        self._kwargs = kwargs

    async def execute(self) -> Response:
        idempotency_key = RequestInspector.extract_idempotency_key(self._request)
        if idempotency_key is None:
            return await self._handle_missing_key()

        if self._store is None:
            return await self._handle_missing_store()

        return await self._run_under_lock(idempotency_key)

    async def _handle_missing_key(self) -> Response:
        if self._required:
            raise IdempotencyKeyRequired()
        return await self._invoke_view()

    async def _handle_missing_store(self) -> Response:
        if self._required:
            raise IdempotencyUnavailable()
        warn_store_not_configured()
        return await self._invoke_view()

    async def _run_under_lock(self, idempotency_key: str) -> Response:
        assert self._store is not None
        store = self._store

        user_id = RequestInspector.extract_user_id(self._request)
        request_hash = fingerprint(
            self._request.method,
            self._request.path,
            self._request.data,
        )
        acquire_outcome = await self._try_acquire_or_fallback(
            store,
            user_id,
            idempotency_key,
            request_hash,
        )
        if acquire_outcome is None:
            return await self._invoke_view()

        if isinstance(acquire_outcome, AlreadyCompleted):
            return ReplayResponseBuilder.build(acquire_outcome.response)
        if isinstance(acquire_outcome, InProgress):
            raise IdempotencyInFlight()
        if isinstance(acquire_outcome, Mismatch):
            raise IdempotencyKeyReused()

        assert isinstance(acquire_outcome, Acquired)
        return await self._invoke_and_persist(
            store,
            user_id,
            idempotency_key,
            request_hash,
        )

    async def _try_acquire_or_fallback(
        self,
        store: RedisIdempotencyStore,
        user_id: int | str,
        idempotency_key: str,
        request_hash: str,
    ) -> AcquireResult | None:
        try:
            return await store.try_acquire(
                user_id,
                idempotency_key,
                request_hash,
            )
        except StoreUnavailable as exc:
            warn_store_unavailable_on_acquire(exc, self._required)
            if self._required:
                raise IdempotencyUnavailable() from exc
            return None

    async def _invoke_and_persist(
        self,
        store: RedisIdempotencyStore,
        user_id: int | str,
        idempotency_key: str,
        request_hash: str,
    ) -> Response:
        try:
            view_response = await self._invoke_view()
        except BaseException:
            await store.release_lock(user_id, idempotency_key)
            raise

        if _is_successful_status(view_response.status_code):
            await self._cache_response_best_effort(
                store,
                view_response,
                user_id,
                idempotency_key,
                request_hash,
            )
        else:
            await store.release_lock(user_id, idempotency_key)
        return view_response

    async def _cache_response_best_effort(
        self,
        store: RedisIdempotencyStore,
        view_response: Response,
        user_id: int | str,
        idempotency_key: str,
        request_hash: str,
    ) -> None:
        try:
            await store.store_response(
                user_id,
                idempotency_key,
                request_hash=request_hash,
                status_code=view_response.status_code,
                body=view_response.data,
                headers=dict(view_response.headers),
            )
        except StoreUnavailable as exc:
            warn_store_unavailable_on_store(exc)

    async def _invoke_view(self) -> Response:
        response = await self._view_callable(
            self._view_self,
            self._request,
            *self._args,
            **self._kwargs,
        )

        return mark_replay(response, replayed=False)
