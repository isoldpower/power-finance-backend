from abc import ABC, abstractmethod

from django.contrib.auth.models import User

from ..dtos import AuthenticatedPrincipal


class SyncAuthenticatedUser(ABC):
    @abstractmethod
    def execute(self, principal: AuthenticatedPrincipal) -> User:
        raise NotImplementedError()