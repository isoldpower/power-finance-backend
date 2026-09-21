from dataclasses import dataclass

from data_write_core.domain.entities import InternalUserEntity

from .preferences import UserPreferences


@dataclass(frozen=True)
class GatewayUser:
    internal: InternalUserEntity
    preferences: UserPreferences

    @property
    def unique_id(self) -> str:
        return self.internal.unique_id

    @property
    def external_id(self) -> str:
        return self.internal.external_id
