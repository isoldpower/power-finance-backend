from dataclasses import dataclass
from typing import Any

from .preferences import UserPreferences


@dataclass(frozen=True)
class GatewayUser:
    internal: Any
    preferences: UserPreferences

    @property
    def id(self) -> int:
        return self.internal.id

    @property
    def external_id(self) -> str:
        return self.internal.username

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False
