from __future__ import annotations

from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any
from unittest import IsolatedAsyncioTestCase

from rest_framework import status
from rest_framework.response import Response

from write_service.common.idempotency.atomic_redis import (
    Acquired,
    AlreadyCompleted,
    InProgress,
    Mismatch,
    StoredResponse,
)
from write_service.common.idempotency.decorator import (
    IDEMPOTENCY_HEADER,
    get_store,
    idempotent,
    set_store,
)
from write_service.common.idempotency.exceptions import (
    IdempotencyInFlight,
    IdempotencyKeyRequired,
    IdempotencyKeyReused,
    IdempotencyUnavailable,
    StoreUnavailable,
)


@dataclass
class _FakeEntry:
    request_hash: str
    state: str
    response: StoredResponse | None = None


@dataclass
class FakeStore:
    """In-memory stand-in for RedisIdempotencyStore. Same surface, no Lua."""

    entries: dict[str, _FakeEntry] = field(default_factory=dict)
    raise_on_acquire: bool = False
    raise_on_store: bool = False
    acquire_calls: int = 0

    def _key(self, user_id, k):
        return f"{user_id}:{k}"

    async def try_acquire(self, user_id, key, request_hash):
        self.acquire_calls += 1
        if self.raise_on_acquire:
            raise StoreUnavailable("redis down")
        slot = self._key(user_id, key)
        existing = self.entries.get(slot)
        if existing is None:
            self.entries[slot] = _FakeEntry(request_hash=request_hash, state="in_flight")
            return Acquired()
        if existing.request_hash != request_hash:
            return Mismatch(stored_hash=existing.request_hash)
        if existing.state == "completed":
            return AlreadyCompleted(response=existing.response)
        return InProgress()

    async def store_response(self, user_id, key, *, request_hash, status_code, body, headers=None):
        if self.raise_on_store:
            raise StoreUnavailable("redis down on write")
        self.entries[self._key(user_id, key)] = _FakeEntry(
            request_hash=request_hash,
            state="completed",
            response=StoredResponse(
                status_code=status_code,
                body=body,
                headers=headers or {},
                request_hash=request_hash,
            ),
        )

    async def release_lock(self, user_id, key):
        self.entries.pop(self._key(user_id, key), None)


def _make_request(
    *,
    method: str = "POST",
    path: str = "/api/v1/transactions/",
    body: Any = None,
    headers: dict[str, str] | None = None,
    user_id: int = 42,
) -> SimpleNamespace:
    """Stub Request with the surface the decorator inspects."""
    return SimpleNamespace(
        method=method,
        path=path,
        data=body if body is not None else {},
        headers=headers or {},
        user=SimpleNamespace(unique_id=user_id),
    )


class IdempotentDecoratorTests(IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.store = FakeStore()
        self._previous_store = get_store()
        set_store(self.store)
        self.handler_calls = 0

    def tearDown(self) -> None:
        set_store(self._previous_store)

    def _view(self, *, required: bool, response: Response | None = None):
        view = self

        @idempotent(required=required)
        async def post(self_view, request):
            view.handler_calls += 1
            return response or Response({"id": 1}, status=status.HTTP_201_CREATED)

        return post

    async def test_success_caches_response_and_replay_returns_cached(self) -> None:
        view = self._view(required=True)
        req = _make_request(headers={IDEMPOTENCY_HEADER: "k-1"}, body={"amount": "10"})

        first = await view(self, req)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(self.handler_calls, 1)

        replay = await view(self, req)
        self.assertEqual(replay.status_code, 201)
        self.assertEqual(replay["Idempotent-Replayed"], "true")
        self.assertEqual(self.handler_calls, 1)

    async def test_same_key_different_body_returns_422(self) -> None:
        view = self._view(required=True)
        req_a = _make_request(headers={IDEMPOTENCY_HEADER: "k-2"}, body={"amount": "10"})
        await view(self, req_a)

        req_b = _make_request(headers={IDEMPOTENCY_HEADER: "k-2"}, body={"amount": "999"})
        with self.assertRaises(IdempotencyKeyReused):
            await view(self, req_b)

    async def test_in_flight_returns_409(self) -> None:
        view = self._view(required=True)
        from write_service.common.idempotency.request_hash import fingerprint

        body = {"amount": "10"}
        req = _make_request(headers={IDEMPOTENCY_HEADER: "k-3"}, body=body)
        h = fingerprint(req.method, req.path, body)
        self.store.entries[f"{req.user.unique_id}:k-3"] = _FakeEntry(
            request_hash=h, state="in_flight"
        )

        with self.assertRaises(IdempotencyInFlight):
            await view(self, req)
        self.assertEqual(self.handler_calls, 0)

    async def test_missing_key_required_raises_400(self) -> None:
        view = self._view(required=True)
        req = _make_request(headers={})
        with self.assertRaises(IdempotencyKeyRequired):
            await view(self, req)

    async def test_missing_key_optional_passes_through(self) -> None:
        view = self._view(required=False)
        req = _make_request(headers={})
        response = await view(self, req)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.handler_calls, 1)
        self.assertEqual(self.store.acquire_calls, 0)

    async def test_redis_unavailable_required_raises_503(self) -> None:
        self.store.raise_on_acquire = True
        view = self._view(required=True)
        req = _make_request(headers={IDEMPOTENCY_HEADER: "k-4"})
        with self.assertRaises(IdempotencyUnavailable):
            await view(self, req)

    async def test_redis_unavailable_optional_passes_through(self) -> None:
        self.store.raise_on_acquire = True
        view = self._view(required=False)
        req = _make_request(headers={IDEMPOTENCY_HEADER: "k-5"})
        response = await view(self, req)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.handler_calls, 1)

    async def test_error_response_releases_lock(self) -> None:
        error_response = Response({"error": "boom"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        view = self._view(required=True, response=error_response)
        req = _make_request(headers={IDEMPOTENCY_HEADER: "k-6"})
        await view(self, req)

        view2 = self._view(required=True)
        retry = await view2(self, req)
        self.assertEqual(retry.status_code, 201)

    async def test_handler_exception_releases_lock(self) -> None:
        view = self
        boom = RuntimeError("kaboom")

        @idempotent(required=True)
        async def post(self_view, request):
            view.handler_calls += 1
            raise boom

        req = _make_request(headers={IDEMPOTENCY_HEADER: "k-7"})
        with self.assertRaises(RuntimeError):
            await post(self, req)

        @idempotent(required=True)
        async def post_ok(self_view, request):
            view.handler_calls += 1
            return Response({"ok": True}, status=200)

        response = await post_ok(self, req)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.handler_calls, 2)
