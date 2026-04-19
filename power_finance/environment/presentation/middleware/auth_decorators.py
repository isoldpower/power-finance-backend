import logging
from functools import wraps
from typing import Callable, ParamSpec, TypeVar
from django.http import HttpResponse
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from .jwt_authentication import ClerkJWTAuthentication

logger = logging.getLogger(__name__)


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
                auth_result = await auth_class.authenticate(request)
                if auth_result:
                    request.user, _ = auth_result
                else:
                    return HttpResponse(
                        "Received unauthorized request.",
                        status=status.HTTP_401_UNAUTHORIZED
                    )
            except AuthenticationFailed as e:
                logger.warning(e)
                return HttpResponse(
                    "Authorization error occurred on endpoint",
                    status=status.HTTP_401_UNAUTHORIZED
                )

            return await function(request, *args, **kwargs)
        return wrapped
    return decorator
