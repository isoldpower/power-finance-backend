from collections.abc import Sequence
from datetime import UTC, datetime

from kafka_consumer_py import Effect, EventMessage
from kafka_messages import UserSynced

from service_core.shared.logging import log_template_accounts_seeded
from service_core.shared.payloads import decode_payload

from .contracts import TemplateAccount
from .events import account_created
from .infrastructure import SqlAlchemySeedUnitOfWork
from .repositories import UnitOfWorkFactory


class SeedTemplateAccounts(Effect):
    def __init__(
        self,
        template: Sequence[TemplateAccount],
        unit_of_work: UnitOfWorkFactory = SqlAlchemySeedUnitOfWork,
    ) -> None:
        self._template = tuple(template)
        self._unit_of_work = unit_of_work

    async def apply(self, event: EventMessage) -> None:
        payload = decode_payload(event, UserSynced)
        now = datetime.now(UTC)

        async with self._unit_of_work() as work:
            await work.users.remember(payload.user_id, payload.external_id, now)

            created_accounts = await work.accounts.ensure(
                payload.user_id,
                [account.specification for account in self._template],
                now,
            )

            await work.outbox.publish(
                [
                    account_created(
                        account,
                        user_id=payload.user_id,
                        user_external_id=payload.external_id,
                    )
                    for account in created_accounts
                ]
            )

        log_template_accounts_seeded(
            payload.user_id,
            len(created_accounts),
        )
