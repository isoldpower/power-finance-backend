from abc import ABC, abstractmethod

from environment.application.dtos import ExternalUserInfo


class ExternalAuth(ABC):
    @abstractmethod
    def resolve_auth_token(self, received_header: str) -> str | None:
        raise NotImplementedError()

    @abstractmethod
    async def fetch_user_info(self, user_id: str) -> ExternalUserInfo | None:
        raise NotImplementedError()

    @abstractmethod
    async def get_jwks(self) -> dict:
        raise NotImplementedError()