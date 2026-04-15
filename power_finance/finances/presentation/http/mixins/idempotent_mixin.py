import json
import logging
from django.http import HttpResponse
from rest_framework.renderers import JSONRenderer

from finances.application.bootstrap import get_redis_client
from finances.application.use_cases.workflows import (
    IdempotencyService,
    IdempotencyInFlightError,
    IdempotencyCachedError,
)

from .exceptions import (
    IdempotencyKeyMissingError,
    IdempotencyInFlightError as IdempotencyInFlightApiError,
)

logger = logging.getLogger(__name__)


class _CachedResponseSignal(Exception):
    def __init__(self, status_code: int, body: bytes):
        self.status_code = status_code
        self.body = body


class IdempotentMixin:
    """
    DRF ViewSet mixin that enforces idempotency on specified actions.
    Delegates key logic to IdempotencyService (application layer).

    Usage:
        class MyViewSet(IdempotentMixin, APIView):
            IDEMPOTENT_ACTIONS = {'post', 'patch', 'delete'}
    """
    IDEMPOTENT_ACTIONS: set[str] = set()
    _idempotency_key_acquired: bool = False

    def _get_idempotency_service(self) -> IdempotencyService:
        return IdempotencyService(redis=get_redis_client(sync=True))

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)

        if request.method.lower() not in self.IDEMPOTENT_ACTIONS:
            return
        key = request.headers.get("Idempotency-Key")
        if not key:
            raise IdempotencyKeyMissingError()

        try:
            service = self._get_idempotency_service()
            service.check_and_acquire(request.user.id, key)
            self._idempotency_key_acquired = True
        except IdempotencyInFlightError:
            raise IdempotencyInFlightApiError()
        except IdempotencyCachedError as e:
            cached = json.loads(e.payload)
            raise _CachedResponseSignal(
                status_code=cached["status_code"],
                body=cached["body"].encode(),
            )

    def handle_exception(self, exc):
        if isinstance(exc, _CachedResponseSignal):
            return HttpResponse(
                content=exc.body,
                content_type="application/json",
                status=exc.status_code,
            )
        return super().handle_exception(exc)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        if not getattr(self, '_idempotency_key_acquired', False):
            return response

        key = request.headers.get("Idempotency-Key")
        service = self._get_idempotency_service()

        if response.status_code < 400:
            body = JSONRenderer().render(response.data)
            payload = json.dumps({
                "status_code": response.status_code,
                "body": body.decode(),
            }).encode()
            service.store(request.user.id, key, payload)
        else:
            service.release(request.user.id, key)

        return response
