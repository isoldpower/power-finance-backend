from dataclasses import dataclass
from datetime import datetime

from data_write_core.domain.value_objects.demo_identity import demo_external_id_for_visit

from ...bootstrap import get_repository_registry
from ...interfaces import UserRepository
from ...interfaces.demo_token_issuer import DemoTokenIssuer
from ...interfaces.demo_visit_codec import DemoVisit
from .demo_account_seed import DemoAccountSeeder


@dataclass(frozen=True)
class StartDemoSessionCommand:
    visit: DemoVisit


@dataclass(frozen=True)
class DemoSessionDTO:
    token: str
    expires_at: datetime
    external_id: str
    write_version: int | None


class StartDemoSessionCommandHandler:
    def __init__(
        self,
        token_issuer: DemoTokenIssuer,
        user_repository: UserRepository | None = None,
        account_seeder: DemoAccountSeeder | None = None,
    ) -> None:
        self._token_issuer = token_issuer
        self._user_repository = user_repository or get_repository_registry().user_repository
        self._account_seeder = account_seeder or DemoAccountSeeder()

    async def handle(self, command: StartDemoSessionCommand) -> DemoSessionDTO:
        external_id = demo_external_id_for_visit(command.visit.nonce)
        demo_user = await self._user_repository.get_synced_internal(external_id=external_id)
        write_version = await self._account_seeder.seed_if_incomplete(
            int(demo_user.unique_id), external_id
        )
        issued_token = self._token_issuer.issue(external_id, not_after=command.visit.expires_at)

        return DemoSessionDTO(
            token=issued_token.token,
            expires_at=issued_token.expires_at,
            external_id=external_id,
            write_version=write_version,
        )
