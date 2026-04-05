from functools import wraps
from http import HTTPStatus
from typing import Callable, ParamSpec, TypeVar

from asgiref.sync import sync_to_async
from django.http import HttpResponse
from rest_framework.authentication import BaseAuthentication
from rest_framework.request import Request

from identity.presentation.jwt_authentication import ClerkJWTAuthentication


P = ParamSpec("P")
R = TypeVar("R")

def async_with_auth(
        authenticator: BaseAuthentication | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        async def wrapped(request: Request, *args: P.args, **kwargs: P.kwargs) -> R:
            auth_class = authenticator or ClerkJWTAuthentication()
            try:
                auth_result = await sync_to_async(auth_class.authenticate)(request)
                if auth_result:
                    user, token = auth_result
                    request.user = user
                else:
                    return HttpResponse("Received unauthorized request.", status=HTTPStatus.UNAUTHORIZED)
            except Exception as e:
                return HttpResponse(f"Authorization error: {e}", status=HTTPStatus.UNAUTHORIZED)

            return await function(request, *args, **kwargs)
        return wrapped
    return decorator
