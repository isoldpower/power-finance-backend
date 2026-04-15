# Async Migration

## Why

Django is synchronous by default. Every request occupies a thread from the moment it arrives until it returns a response. For a financial backend, this is expensive: authentication hits Clerk's API over HTTP, every DB query blocks, every Redis call blocks. Under load, the thread pool saturates before the CPU does — the server is idle while threads wait on I/O.

Migrating to async eliminates that waste. A single async worker can handle hundreds of concurrent in-flight requests with far fewer threads. The I/O-bound nature of this backend (external auth, PostgreSQL, Redis, RabbitMQ) makes it a strong candidate: the bottleneck is always waiting, not computing.

This is also table-stakes knowledge. Async Django is the production standard for any new Python backend that expects real traffic.

## Production Concepts Taught

- ASGI vs. WSGI — protocol differences, how Django handles both
- `async def` views in DRF — what DRF 3.14+ supports natively
- `sync_to_async` / `async_to_sync` — bridging sync and async code safely
- Django async ORM — `aget`, `acreate`, `afilter`, `aupdate`, `adelete`, `aexists`
- `contextvars` — replacing `threading.local` for per-request state in async context
- `httpx.AsyncClient` — async HTTP vs. `requests` (which blocks the event loop)
- Django async cache API — `acache.aget`, `acache.aset`
- Async DRF authentication and throttling
- Celery isolation — why Celery stays sync and how it coexists with async Django
- Connection pooling under ASGI — why `CONN_MAX_AGE` and thread-local connections break
- `asyncio` event loop lifecycle — one loop per worker, not one per request

## Current Stack Inventory

Every layer that blocks the event loop must be migrated. Current state:

| Layer | Current | Blocks event loop? |
|---|---|---|
| Server | `WSGI_APPLICATION` (gunicorn) | Yes — by design |
| Views | sync `APIView` | Yes |
| Authentication | sync `BaseAuthentication.authenticate` | Yes |
| Throttling | sync `BaseThrottle.allow_request` | Yes |
| Use cases | sync `handle()` | Yes |
| External HTTP (Clerk) | `requests.get` | Yes — blocks thread |
| ORM (UserRepository) | `User.objects.get`, `get_or_create` | Yes |
| Cache | `cache.get` / `cache.set` | Yes |

Target state: everything async except Celery tasks.

## Migration Layers

### Layer 1 — Server: WSGI → ASGI + uvicorn

`asgi.py` already exists. Switch the server:

```python
# settings.py — replace WSGI_APPLICATION with ASGI_APPLICATION
# WSGI_APPLICATION = 'power_finance.wsgi.application'   ← remove
ASGI_APPLICATION = 'power_finance.asgi.application'
```

```dockerfile
# Dockerfile — replace gunicorn with uvicorn
# CMD ["gunicorn", "power_finance.wsgi:application"]   ← old
CMD ["uvicorn", "power_finance.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

```
# requirements.txt
uvicorn[standard]==0.34.0      # replaces gunicorn for ASGI
httpx==0.28.1                  # replaces requests for async HTTP
```

**Critical**: `CONN_MAX_AGE` must stay `0` under ASGI. Django's database connection handling is thread-local. Under ASGI, multiple coroutines share a thread — persistent connections corrupt each other. Django 4.2+ uses per-coroutine connections when running async, but `CONN_MAX_AGE > 0` re-enables thread-local pooling, which is unsafe. Keep it `0` or use an external connection pooler (PgBouncer).

```python
# settings.py
DATABASES = {
    'default': {
        ...
        'CONN_MAX_AGE': 0,   # ← required under ASGI
    }
}
```

---

### Layer 2 — Views: sync APIView → async

DRF `APIView` supports async handlers directly. Declare handler methods as `async def`:

```python
# Before
class WalletListView(APIView):
    def get(self, request):
        wallets = WalletQueryHandler().handle(GetWalletsQuery(user_id=request.user.id))
        return Response(WalletSerializer(wallets, many=True).data)

# After
class WalletListView(APIView):
    async def get(self, request):
        wallets = await WalletQueryHandler().handle(GetWalletsQuery(user_id=request.user.id))
        return Response(WalletSerializer(wallets, many=True).data)
```

DRF detects `async def` and wraps the view appropriately when running under ASGI. No subclassing required — `APIView` handles both sync and async handlers depending on what you declare.

**Note on DRF serializers**: serializers remain sync. Calling `serializer.is_valid()` or `.save()` from an async view is safe as long as those methods don't touch the ORM directly — if they do, wrap with `sync_to_async`. Prefer moving ORM work to use cases/repositories rather than serializer `save()` in async code.

---

### Layer 3 — Authentication: async `ClerkJWTAuthentication`

DRF 3.14+ supports `async def authenticate`. Two approaches:

#### Option A — `sync_to_async` wrapper (migration step)

Zero changes to use cases or infrastructure. Correct starting point.

```python
# environment/presentation/middleware/jwt_authentication.py
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from environment.application.use_cases import AuthenticateUserCommandHandler, AuthenticateUserCommand


class ClerkJWTAuthentication(BaseAuthentication):
    def __init__(self):
        self.authentication_handler = AuthenticateUserCommandHandler()

    async def authenticate(self, request: Request) -> tuple[User, str] | None:
        if request.method == "OPTIONS":
            return None
        try:
            return await sync_to_async(self.authentication_handler.handle)(
                AuthenticateUserCommand(auth_header=request.headers.get("Authorization", ""))
            )
        except Exception as e:
            raise AuthenticationFailed from e
```

`sync_to_async` runs the blocking function in Django's thread pool executor. The event loop is not blocked — it suspends the coroutine and resumes when the thread completes. Functionally correct. The thread pool is still used, but the event loop can service other requests while waiting.

#### Option B — Fully async authentication (final state)

`authenticate` calls async use case; no thread pool involved. See Layers 4–6 for the prerequisite changes.

```python
class ClerkJWTAuthentication(BaseAuthentication):
    def __init__(self):
        self.authentication_handler = AuthenticateUserCommandHandler()

    async def authenticate(self, request: Request) -> tuple[User, str] | None:
        if request.method == "OPTIONS":
            return None
        try:
            return await self.authentication_handler.handle(
                AuthenticateUserCommand(auth_header=request.headers.get("Authorization", ""))
            )
        except Exception as e:
            raise AuthenticationFailed from e
```

---

### Layer 4 — External HTTP: `requests` → `httpx`

`requests.get` is synchronous and blocks the event loop. `httpx.AsyncClient` is the drop-in async replacement.

```python
# environment/infrastructure/integration/authentication/clerk_sdk.py
import httpx
import datetime
import pytz

from rest_framework.exceptions import AuthenticationFailed
from environment.application.dtos import ExternalUserInfo
from environment.application.interfaces import ExternalAuth


class ClerkAuth(ExternalAuth):
    def __init__(self, issuer_url: str, secret_key: str, api_base_url: str):
        self._issuer_url = issuer_url
        self._secret_key = secret_key
        self._api_base_url = api_base_url
        self._headers = {"Authorization": f"Bearer {self._secret_key}"}

    async def get_jwks(self) -> dict:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self._issuer_url}/.well-known/jwks.json",
                    headers=self._headers,
                    timeout=10,
                )
            except httpx.RequestError as exc:
                raise AuthenticationFailed(f"Failed to fetch JWKS from Clerk: {exc}") from exc

        if response.status_code != 200:
            raise AuthenticationFailed("Failed to fetch JWKS from Clerk.")

        return response.json()

    async def fetch_user_info(self, user_id: str) -> ExternalUserInfo | None:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self._api_base_url}/users/{user_id}",
                    headers=self._headers,
                    timeout=10,
                )
            except httpx.RequestError as exc:
                raise AuthenticationFailed(f"Failed to fetch Clerk user info: {exc}") from exc

        if response.status_code == 404:
            return None
        if response.status_code != 200:
            raise AuthenticationFailed("Failed to fetch user info from Clerk.")

        data = response.json()
        email_addresses = data.get("email_addresses") or []
        email_address = email_addresses[0].get("email_address") if email_addresses else None

        last_sign_in_at = data.get("last_sign_in_at")
        last_login = (
            datetime.datetime.fromtimestamp(last_sign_in_at / 1000, tz=pytz.UTC)
            if last_sign_in_at is not None else None
        )

        return ExternalUserInfo(
            external_user_id=user_id,
            email_address=email_address,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            last_login=last_login,
        )

    def resolve_auth_token(self, received_header: str) -> str | None:
        if not received_header:
            return None
        parts = received_header.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise AuthenticationFailed("Authorization token format is invalid. Expected Bearer token.")
        return parts[1]
```

**`httpx.AsyncClient` lifetime**: creating a new client per call (as above) is simple and correct. For high throughput, create a single shared client at application startup and reuse it — this enables connection pooling and keep-alive across requests. Use lifespan events in `asgi.py`:

```python
# asgi.py
from contextlib import asynccontextmanager
import httpx
from django.core.asgi import get_asgi_application

_http_client: httpx.AsyncClient | None = None

def get_http_client() -> httpx.AsyncClient:
    return _http_client

@asynccontextmanager
async def lifespan(app):
    global _http_client
    _http_client = httpx.AsyncClient(timeout=10)
    yield
    await _http_client.aclose()

application = get_asgi_application()
```

Then inject `get_http_client()` into `ClerkAuth` rather than creating a new client per call.

**Update the `ExternalAuth` interface** to match:

```python
# environment/application/interfaces/external_auth.py
from abc import ABC, abstractmethod
from environment.application.dtos import ExternalUserInfo


class ExternalAuth(ABC):
    @abstractmethod
    async def resolve_auth_token(self, received_header: str) -> str | None: ...

    @abstractmethod
    async def fetch_user_info(self, user_id: str) -> ExternalUserInfo | None: ...

    @abstractmethod
    async def get_jwks(self) -> dict: ...
```

---

### Layer 5 — ORM: sync → async Django ORM

Django 4.1+ provides native async ORM methods. Every `QuerySet` method has an `a`-prefixed async version:

| Sync | Async |
|---|---|
| `Model.objects.get(...)` | `await Model.objects.aget(...)` |
| `Model.objects.get_or_create(...)` | `await Model.objects.aget_or_create(...)` |
| `Model.objects.filter(...).first()` | `await Model.objects.filter(...).afirst()` |
| `queryset.count()` | `await queryset.acount()` |
| `instance.save()` | `await instance.asave()` |
| `instance.delete()` | `await instance.adelete()` |
| `async for item in queryset` | native async iteration |

```python
# environment/infrastructure/repositories/django_user_repository.py
from django.contrib.auth.models import User
from environment.application.interfaces import UserRepository
from environment.domain.entities import UserEntity
from ..mappers import UserMapper


class DjangoUserRepository(UserRepository):
    async def get_or_create_by_external_id(self, external_user_id: str) -> UserEntity:
        user, _ = await User.objects.aget_or_create(username=external_user_id)
        return UserMapper.to_domain(user)

    async def update_user_info(self, user: UserEntity) -> UserEntity:
        updated_user: User = await User.objects.aget(username=user.id)
        modified_fields = UserMapper.get_changed_fields(updated_user, user)

        if len(modified_fields) > 0:
            UserMapper.update_model(updated_user, user)
            await updated_user.asave(update_fields=modified_fields)

        return UserMapper.to_domain(updated_user)

    async def get_user_raw(self, user: UserEntity) -> User:
        return await User.objects.aget(username=user.id)
```

**Update the `UserRepository` interface** to reflect async signatures:

```python
# environment/application/interfaces/user_repository.py
from abc import ABC, abstractmethod
from django.contrib.auth.models import User
from environment.domain.entities import UserEntity


class UserRepository(ABC):
    @abstractmethod
    async def get_or_create_by_external_id(self, external_user_id: str) -> UserEntity: ...

    @abstractmethod
    async def update_user_info(self, user: UserEntity) -> UserEntity: ...

    @abstractmethod
    async def get_user_raw(self, user: UserEntity) -> User: ...
```

---

### Layer 6 — Cache: `DjangoCacheStorage` → async

Django's cache framework has async methods since Django 4.1:

```python
# environment/infrastructure/cache/django_cache.py
from typing import Callable, TypeVar, Awaitable
from django.core.cache import cache, BaseCache
from environment.application.interfaces import CacheStorage

TValue = TypeVar("TValue", bound=object)


class DjangoCacheStorage(CacheStorage):
    cache_instance: BaseCache
    base_cache_key: str

    def __init__(self, cache_key: str):
        self.cache_instance = cache
        self.base_cache_key = cache_key

    async def get_data(
        self,
        callback: Callable[[], Awaitable[TValue]],
        key: str | None = None,
    ) -> TValue:
        final_key = f'{self.base_cache_key}{f":{key}" if key else ""}'
        requested_data = await self.cache_instance.aget(final_key)

        if requested_data:
            data = requested_data
        else:
            data = await callback()

        await self.cache_instance.aset(final_key, data)
        return data
```

**Update the `CacheStorage` interface**:

```python
# environment/application/interfaces/cache_storage.py
from abc import ABC, abstractmethod
from typing import Callable, TypeVar, Awaitable

TValue = TypeVar("TValue", bound=object)


class CacheStorage(ABC):
    @abstractmethod
    async def get_data(
        self,
        callback: Callable[[], Awaitable[TValue]],
        key: str | None = None,
    ) -> TValue: ...
```

---

### Layer 7 — Use Case: async `AuthenticateUserCommandHandler`

With Layers 4–6 complete, the use case becomes straightforward:

```python
# environment/application/use_cases/authenticate_user.py
import hashlib
from dataclasses import dataclass
from django.conf import settings
from django.contrib.auth.models import User

from ..interfaces import ExternalAuth, UserRepository, CacheStorage
from environment.domain.services import decode_jwt_contents
from environment.domain.entities import UserEntity
from environment.infrastructure.integration import ClerkAuth
from environment.infrastructure.repositories import DjangoUserRepository
from environment.infrastructure.cache import DjangoCacheStorage


@dataclass(frozen=True)
class AuthenticateUserCommand:
    auth_header: str


class AuthenticateUserCommandHandler:
    _external_auth: ExternalAuth
    _user_repository: UserRepository
    _cache_storage: CacheStorage
    _jwks_cache_key: str

    def __init__(
        self,
        user_repository: UserRepository | None = None,
        external_auth: ExternalAuth | None = None,
    ):
        self._user_repository = user_repository or DjangoUserRepository()
        self._jwks_cache_key = "jwks"
        self._cache_storage = DjangoCacheStorage(settings.RESOLVED_ENV["CLERK_CACHE_KEY"])
        self._external_auth = external_auth or ClerkAuth(
            issuer_url=settings.RESOLVED_ENV["CLERK_API_URL"],
            secret_key=settings.RESOLVED_ENV["CLERK_SECRET_KEY"],
            api_base_url="https://api.clerk.com/v1",
        )

    async def _get_user_from_api(self, token: str) -> UserEntity:
        auth_jwks = await self._cache_storage.get_data(
            self._external_auth.get_jwks, self._jwks_cache_key
        )
        principal = decode_jwt_contents(token, auth_jwks)
        external_user = await self._external_auth.fetch_user_info(principal.external_user_id)
        internal_user = await self._user_repository.get_or_create_by_external_id(
            principal.external_user_id
        )
        internal_user.sync_with_external(external_user)
        return await self._user_repository.update_user_info(internal_user)

    def _build_user_hash(self, token: str) -> str:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return f"user_{token_hash}"

    async def handle(self, command: AuthenticateUserCommand) -> tuple[User, str] | None:
        token = self._external_auth.resolve_auth_token(command.auth_header)
        if not token:
            return None

        user_entity: UserEntity = await self._cache_storage.get_data(
            lambda: self._get_user_from_api(token),
            self._build_user_hash(token),
        )
        user_model = await self._user_repository.get_user_raw(user_entity)
        return user_model, token
```

---

### Layer 8 — Throttling: async `BaseThrottle`

DRF 3.14+ supports `async def allow_request`. The existing Redis throttles (`AnonRedisThrottle`, `UserRedisThrottle`, `WriteThrottle`) need the same treatment as authentication — either wrap with `sync_to_async` or rewrite using `aioredis` / `redis.asyncio`:

```python
# Option A: sync_to_async wrapper (migration step)
from asgiref.sync import sync_to_async
from rest_framework.throttling import BaseThrottle


class AsyncRedisThrottleMixin:
    async def allow_request(self, request, view):
        return await sync_to_async(super().allow_request)(request, view)

    async def wait(self):
        return await sync_to_async(super().wait)()


class AnonRedisThrottle(AsyncRedisThrottleMixin, BaseAnonRedisThrottle): ...
class UserRedisThrottle(AsyncRedisThrottleMixin, BaseUserRedisThrottle): ...
```

```python
# Option B: native async using redis.asyncio
import redis.asyncio as aioredis

class UserRedisThrottle(BaseThrottle):
    async def allow_request(self, request, view) -> bool:
        client = aioredis.from_url(REDIS_URL)
        key = self._build_key(request)
        now = time.time()
        window_start = now - 60

        pipe = client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, 60)
        results = await pipe.execute()
        await client.aclose()

        count = results[2]
        self.now = now
        self.num_requests = self.get_rate()
        return count <= self.num_requests
```

---

### Layer 9 — Celery: stays sync

Celery workers run their own event loop per task (via `asyncio.run` if using `CELERY_TASK_ALWAYS_EAGER = False`). Mixing Django async ORM into Celery tasks requires care:

```python
# Option A: keep Celery tasks sync, use sync_to_async inside if needed
@app.task
def process_webhook_delivery(payload_id: str):
    # Sync ORM — fine in Celery worker context
    payload = WebhookPayload.objects.get(id=payload_id)
    ...

# Option B: async Celery tasks (Celery 5.x supports this)
@app.task
async def process_webhook_delivery(payload_id: str):
    payload = await WebhookPayload.objects.aget(id=payload_id)
    async with httpx.AsyncClient() as client:
        await client.post(payload.target_url, json=payload.data)
```

Async Celery tasks require `CELERY_TASK_SERIALIZER = 'json'` and a worker configured with `--pool solo` or `gevent`/`eventlet` for async support. The complexity cost is real — keep Celery sync unless there is a measured reason to change it.

---

## Migration Strategy

Migrate layer by layer. Each layer is independently deployable and testable. Do not migrate everything at once.

```
Phase 1 — Server switch (no code changes to business logic)
  ├── Add uvicorn to requirements.txt
  ├── Set ASGI_APPLICATION in settings.py
  ├── Update Dockerfile CMD
  └── Verify all existing sync views still work under ASGI
      (Django transparently wraps sync views as ASGI-compatible)

Phase 2 — Authentication (Option A: sync_to_async)
  ├── ClerkJWTAuthentication.authenticate → async def + sync_to_async
  └── Deploy and verify auth still works

Phase 3 — External HTTP
  ├── Add httpx to requirements.txt, remove requests
  ├── Rewrite ClerkAuth using httpx.AsyncClient
  ├── Update ExternalAuth interface
  └── Deploy and verify Clerk calls still work

Phase 4 — ORM
  ├── Rewrite DjangoUserRepository with async ORM methods
  ├── Update UserRepository interface
  └── Deploy and verify user creation/lookup still works

Phase 5 — Cache
  ├── Rewrite DjangoCacheStorage with aget/aset
  ├── Update CacheStorage interface
  └── Deploy and verify cache hits/misses still work

Phase 6 — Use case (Option B authentication)
  ├── AuthenticateUserCommandHandler.handle → async def
  ├── ClerkJWTAuthentication.authenticate → remove sync_to_async
  └── Deploy and verify full async auth path

Phase 7 — Views
  ├── Convert views one app at a time (environment → finances → identity)
  └── Verify each app end-to-end before moving to next

Phase 8 — Throttling
  └── Migrate Redis throttles to async
```

**Rollback at each phase**: if a phase introduces regressions, revert that layer only. The `sync_to_async` wrappers in Phases 2–3 are deliberate — they allow the server to run async while business logic migrates incrementally.

---

## Testing Async Code

Standard Django test client is synchronous. Use `AsyncClient` for async views:

```python
# pytest-django + pytest-asyncio
import pytest
from django.test import AsyncClient


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_wallet_list_requires_auth():
    client = AsyncClient()
    response = await client.get("/api/v1/wallets/")
    assert response.status_code == 401


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_authenticate_user_handler(mock_external_auth, mock_user_repository):
    handler = AuthenticateUserCommandHandler(
        user_repository=mock_user_repository,
        external_auth=mock_external_auth,
    )
    result = await handler.handle(AuthenticateUserCommand(auth_header="Bearer test-token"))
    assert result is not None
```

**`transaction=True` is required** for async DB tests. Django's standard test wraps each test in a transaction and rolls back — this doesn't work with `asyncio` because the async code runs in a different context. `transaction=True` uses real transactions and truncates tables between tests instead.

---

## Key Blockwalls

- **`CONN_MAX_AGE > 0` under ASGI** — Django connection handling is thread-local; under ASGI multiple coroutines share a thread. Keep `CONN_MAX_AGE = 0` or use PgBouncer for connection pooling externally.

- **`decode_jwt_contents` is sync** — JWT decoding is CPU-bound, not I/O-bound. It doesn't block the event loop meaningfully (microseconds). Leave it sync and call directly from async code — no `sync_to_async` needed.

- **`threading.local` state in async context** — any per-request state stored in `threading.local` (e.g. tenant context, request-scoped logging) will be shared across concurrent coroutines on the same thread. Replace with `contextvars.ContextVar`.

- **Django middleware is sync** — standard Django middleware runs synchronously even under ASGI. Async middleware requires `__call__` to be `async def` and must use `await self.get_response(request)`. The current `MIDDLEWARE` stack (SecurityMiddleware, CorsMiddleware, etc.) is all Django-provided and handles ASGI correctly — no changes needed there.

- **DRF serializers calling ORM in `.save()`** — `serializer.save()` is sync. If serializer `create()`/`update()` touches the ORM, calling it from an async view will trigger "SynchronousOnlyOperation". Move ORM writes to use cases; serializers should only validate and transform data.

- **`sync_to_async` thread pool exhaustion** — `sync_to_async` uses `asyncio`'s default thread pool executor (default: `min(32, os.cpu_count() + 4)` threads). If every auth call wraps sync work in `sync_to_async`, the thread pool becomes the bottleneck — equivalent to the original WSGI problem. Phase 2–3 wrappers are transitional only, not a final architecture.

- **`httpx.AsyncClient` in `sync_to_async` context** — if you wrap a function that internally uses `httpx.AsyncClient` with `sync_to_async`, it will fail: `httpx.AsyncClient` requires a running event loop, and `sync_to_async` runs in a thread that has no event loop. Migrate HTTP calls (Layer 3) before removing `sync_to_async` wrappers (Layer 6).

- **Django async ORM requires Django 4.1+** — the `a`-prefixed queryset methods (`aget`, `acreate`, etc.) were added in Django 4.1. The project is on Django 5.x so this is satisfied.

- **`pytest-asyncio` mode** — set `asyncio_mode = "auto"` in `pytest.ini` or `pyproject.toml` to avoid decorating every async test with `@pytest.mark.asyncio`. Also add `@pytest.mark.django_db(transaction=True)` to any test that touches the ORM.

- **Celery `AsyncResult` from async context** — calling `task.delay()` from an async view is safe (it's a Redis/RabbitMQ publish, not a coroutine). Calling `result.get()` from async context blocks — never do this in a view. Fire-and-forget or use Celery's callback chain.

- **`contextvars` propagation into threads** — `sync_to_async` copies the current `contextvars` context into the thread automatically (Python 3.7+). `ContextVar` values set in an async view are visible inside `sync_to_async` blocks. The reverse (setting a `ContextVar` inside a thread and reading it from async code after `await`) is not propagated — mutations in threads are invisible to the calling coroutine.
