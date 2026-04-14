from abc import ABC, abstractmethod

from django.contrib.auth.models import User

from environment.domain.entities import UserEntity


class UserRepository(ABC):
    @abstractmethod
    def get_or_create_by_external_id(self, external_user_id: str) -> UserEntity:
        raise NotImplementedError()

    @abstractmethod
    def update_user_info(self, user: UserEntity) -> UserEntity:
        raise NotImplementedError()

    @abstractmethod
    def get_user_raw(self, user: UserEntity) -> User:
        raise NotImplementedError()
