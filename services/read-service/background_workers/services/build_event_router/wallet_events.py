from data_read_core.shared.health_guard import (
    POSTGRES_CONNECTIVITY_ERRORS,
    REDIS_CONNECTIVITY_ERRORS,
    HealthGuardedHandler,
    HealthProbe,
)
from data_read_core.shared.kafka_updates import (
    EventRouter,
    ExecutionPlan,
    SyncProcessGroup,
)
from data_read_core.write_reactions import (
    BumpWalletListVersion,
    CreateWalletReadModel,
    EvictWalletCache,
    RemoveWalletReadModel,
    TrackAppliedSeq,
    UpdateWalletReadModel,
)
from kafka_messages import WalletCreated, WalletDeleted, WalletUpdated


def subscribe_wallet_deleted(
    router: EventRouter,
    postgres_probe: HealthProbe,
    redis_probe: HealthProbe,
):
    wallet_deleted = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(RemoveWalletReadModel(), WalletDeleted),
                    EvictWalletCache(),
                    BumpWalletListVersion(WalletDeleted),
                ]
            ),
        ]
    )
    guarded_handler = HealthGuardedHandler(
        HealthGuardedHandler(
            wallet_deleted,
            postgres_probe,
            guarded_errors=POSTGRES_CONNECTIVITY_ERRORS,
        ),
        redis_probe,
        guarded_errors=REDIS_CONNECTIVITY_ERRORS,
    )

    router.register("WalletDeleted", guarded_handler)


def subscribe_wallet_updated(
    router: EventRouter,
    postgres_probe: HealthProbe,
    redis_probe: HealthProbe,
):
    wallet_updated = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(UpdateWalletReadModel(), WalletUpdated),
                    EvictWalletCache(WalletUpdated),
                    BumpWalletListVersion(WalletUpdated),
                ]
            ),
        ]
    )
    guarded_handler = HealthGuardedHandler(
        HealthGuardedHandler(
            wallet_updated,
            postgres_probe,
            guarded_errors=POSTGRES_CONNECTIVITY_ERRORS,
        ),
        redis_probe,
        guarded_errors=REDIS_CONNECTIVITY_ERRORS,
    )

    router.register("WalletUpdated", guarded_handler)


def subscribe_wallet_created(
    router: EventRouter,
    postgres_probe: HealthProbe,
    redis_probe: HealthProbe,
):
    wallet_created = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(CreateWalletReadModel(), WalletCreated),
                    BumpWalletListVersion(WalletCreated),
                ]
            ),
        ]
    )
    guarded_handler = HealthGuardedHandler(
        HealthGuardedHandler(
            wallet_created,
            postgres_probe,
            guarded_errors=POSTGRES_CONNECTIVITY_ERRORS,
        ),
        redis_probe,
        guarded_errors=REDIS_CONNECTIVITY_ERRORS,
    )

    router.register("WalletCreated", guarded_handler)
