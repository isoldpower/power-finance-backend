from abc import ABC, abstractmethod

from ..dtos import AuthenticatedPrincipal


class JWTDecoder(ABC):
    @abstractmethod
    def decode(self, token: str) -> AuthenticatedPrincipal:
        raise NotImplementedError()