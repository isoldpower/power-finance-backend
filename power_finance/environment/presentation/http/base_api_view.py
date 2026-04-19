from asgiref.sync import iscoroutinefunction, sync_to_async
from rest_framework import exceptions
from rest_framework.views import APIView

from .mixins import ThrottleHeadersMixin, ThrottleExceptionMixin


async def _call(func, *args, **kwargs):
    if iscoroutinefunction(func):
        return await func(*args, **kwargs)
    return await sync_to_async(func)(*args, **kwargs)


async def _call_sync(func, *args, **kwargs):
    if iscoroutinefunction(func):
        return await func(*args, **kwargs)
    return func(*args, **kwargs)


class BaseAPIView(
    ThrottleExceptionMixin,
    ThrottleHeadersMixin,
    APIView
):
    async def perform_authentication(self, request):
        for authenticator in request.authenticators:
            try:
                user_auth_tuple = await _call(authenticator.authenticate, request)
            except exceptions.APIException:
                request._not_authenticated()
                raise
            if user_auth_tuple is not None:
                request._authenticator = authenticator
                request.user, request.auth = user_auth_tuple
                return
        request._not_authenticated()

    async def check_permissions(self, request):
        for permission in self.get_permissions():
            if iscoroutinefunction(permission.has_permission):
                has_perm = await permission.has_permission(request, self)
            else:
                has_perm = permission.has_permission(request, self)
            if not has_perm:
                self.permission_denied(
                    request,
                    message=getattr(permission, 'message', None),
                    code=getattr(permission, 'code', None),
                )

    async def check_throttles(self, request):
        throttle_durations = []
        for throttle in self.get_throttles():
            if iscoroutinefunction(throttle.allow_request):
                allowed = await throttle.allow_request(request, self)
            else:
                allowed = throttle.allow_request(request, self)
            if not allowed:
                throttle_durations.append(throttle.wait())
        if throttle_durations:
            durations = [d for d in throttle_durations if d is not None]
            self.throttled(request, max(durations, default=None))

    async def initial(self, request, *args, **kwargs):
        self.format_kwarg = self.get_format_suffix(**kwargs)
        neg = self.perform_content_negotiation(request)
        request.accepted_renderer, request.accepted_media_type = neg
        version, scheme = self.determine_version(request, *args, **kwargs)
        request.version, request.versioning_scheme = version, scheme
        await self.perform_authentication(request)
        await self.check_permissions(request)
        await self.check_throttles(request)
        hook = getattr(type(self), '_idempotency_initial', None)
        if hook is not None:
            await _call(hook, self, request, *args, **kwargs)

    def handle_exception(self, exc):
        hook = getattr(type(self), '_idempotency_exception', None)
        if hook is not None:
            result = hook(self, exc)
            if result is not None:
                return result
        return super().handle_exception(exc)

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        hook = getattr(type(self), '_idempotency_finalize', None)
        if hook is not None:
            hook(self, request, response)
        return response

    async def dispatch(self, request, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.request = self.initialize_request(request, *args, **kwargs)
        self.headers = self.default_response_headers

        try:
            await _call(self.initial, self.request, *args, **kwargs)

            if self.request.method.lower() in self.http_method_names:
                handler = getattr(self, self.request.method.lower(), self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed

            handler_result = await _call(handler, self.request, *args, **kwargs)
        except Exception as exc:
            handler_result = await _call_sync(self.handle_exception, exc)

        self.response = await _call_sync(
            self.finalize_response,
            self.request,
            handler_result,
            *args,
            **kwargs,
        )
        return self.response
