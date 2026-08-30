from kafka_consumer_py import EventRouter, ExecutionPlan, SyncProcessGroup
from service_core.write_reactions import user_created

from ._health_guards import guard_all
from ._template_accounts import SEED_TEMPLATE_ACCOUNTS
from ._types import ProbesDictionary


def subscribe_user_synced(router: EventRouter, probes: ProbesDictionary) -> None:
    user_synced = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    user_created.SeedTemplateAccounts(SEED_TEMPLATE_ACCOUNTS),
                ]
            ),
        ]
    )

    router.register(
        "UserSynced",
        guard_all(user_synced, probes),
    )
