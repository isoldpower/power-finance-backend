from dataclasses import dataclass
from datetime import datetime

from environment.application.dtos import ExternalUserInfo


@dataclass
class UserEntity:
    id: str
    email: str
    first_name: str
    last_name: str
    last_login: datetime

    @classmethod
    def from_persistence(
            cls,
            id: str,
            email: str,
            first_name: str,
            last_name: str,
            last_login: datetime,
    ):
        return cls(
            id=id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            last_login=last_login,
        )

    def sync_with_external(self, principal: ExternalUserInfo):
        self.email = principal.email_address
        self.first_name = principal.first_name
        self.last_name = principal.last_name
        self.last_login = principal.last_login