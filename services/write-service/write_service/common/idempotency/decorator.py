import functools
from collections.abc import Callable

from rest_framework.response import Response

from .atomic_redis import RedisIdempotencyStore
from .request_inspector import IDEMPOTENCY_HEADER
from .workflow import AsyncViewMethod, IdempotencyWorkflow

_store: RedisIdempotencyStore | None = None


def set_store(store: RedisIdempotencyStore | None) -> None:
    global _store
    _store = store


def get_store() -> RedisIdempotencyStore | None:
    return _store


def idempotent(*, required: bool) -> Callable[[AsyncViewMethod], AsyncViewMethod]:
    def decorator(view_callable: AsyncViewMethod) -> AsyncViewMethod:
        @functools.wraps(view_callable)
        async def wrapper(view_self, request, *args, **kwargs) -> Response:
            workflow = IdempotencyWorkflow(
                store=get_store(),
                required=required,
                view_callable=view_callable,
                view_self=view_self,
                request=request,
                args=args,
                kwargs=kwargs,
            )
            return await workflow.execute()

        return wrapper

    return decorator


__all__ = [
    "IDEMPOTENCY_HEADER",
    "get_store",
    "idempotent",
    "set_store",
]
