from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication
from rest_framework.request import Request

from identity.application.use_cases import AuthenticateUserCommandHandler, AuthenticateUserCommand


class ClerkJWTAuthentication(BaseAuthentication):
    def __init__(self):
        self.authentication_handler = AuthenticateUserCommandHandler()

    def authenticate(self, request: Request) -> User | None:
        if request.method in ["OPTIONS"]:
            return None

        return self.authentication_handler.handle(AuthenticateUserCommand(
            auth_header=request.headers.get("Authorization", "")
        ))