from asgiref.sync import iscoroutinefunction, sync_to_async
from rest_framework import exceptions
from rest_framework.views import APIView


async def _always_async_call(func, *args, **kwargs):
    if iscoroutinefunction(func):
        return await func(*args, **kwargs)
    return await sync_to_async(func)(*args, **kwargs)


class AsyncAPIView(APIView):
    view_is_async = True

    async def perform_authentication(self, request):
        for authenticator in request.authenticators:
            try:
                user_auth_tuple = await _always_async_call(
                    authenticator.authenticate,
                    request,
                )
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
                allowed = await permission.has_permission(request, self)
            else:
                allowed = permission.has_permission(request, self)
            if not allowed:
                self.permission_denied(
                    request,
                    message=getattr(permission, "message", None),
                    code=getattr(permission, "code", None),
                )

    async def check_throttles(self, request):
        durations = []
        for throttle in self.get_throttles():
            if iscoroutinefunction(throttle.allow_request):
                allowed = await throttle.allow_request(request, self)
            else:
                allowed = throttle.allow_request(request, self)
            if not allowed:
                durations.append(throttle.wait())
        durations = [duration for duration in durations if duration is not None]
        if durations:
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

    async def dispatch(self, request, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.request = self.initialize_request(request, *args, **kwargs)
        self.headers = self.default_response_headers

        try:
            await self.initial(self.request, *args, **kwargs)

            if self.request.method.lower() in self.http_method_names:
                handler = getattr(
                    self,
                    self.request.method.lower(),
                    self.http_method_not_allowed,
                )
            else:
                handler = self.http_method_not_allowed

            response = await _always_async_call(
                handler,
                self.request,
                *args,
                **kwargs,
            )
        except Exception as exc:
            response = self.handle_exception(exc)

        self.response = self.finalize_response(
            self.request,
            response,
            *args,
            **kwargs,
        )
        return self.response


def async_api_view(http_method_names):
    methods = [method.lower() for method in http_method_names]

    def decorator(func):
        async def handler(self, request, *args, **kwargs):
            return await func(request, *args, **kwargs)

        handler.__name__ = func.__name__
        view_class = type(
            func.__name__,
            (AsyncAPIView,),
            {method: handler for method in methods},
        )
        view_class.__module__ = func.__module__
        view_class.http_method_names = [*methods, "options"]
        return view_class.as_view()

    return decorator
