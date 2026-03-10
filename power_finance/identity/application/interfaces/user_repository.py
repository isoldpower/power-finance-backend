from abc import ABC, abstractmethod

from django.contrib.auth.models import User


class UserRepository(ABC):
    @abstractmethod
    def get_or_create_by_external_id(self, external_user_id: str) -> User:
        raise NotImplementedError()

    @abstractmethod
    def save(self, user: User) -> None:
        raise NotImplementedError()
