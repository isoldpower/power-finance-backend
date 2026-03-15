from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    external_user_id: str


@dataclass(frozen=True)
class ExternalUserInfo:
    external_user_id: str
    email_address: str | None
    first_name: str | None
    last_name: str | None
    last_login: datetime | None