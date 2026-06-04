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
    BumpTransactionListVersion,
    BumpWalletListVersion,
    CreateTransactionReadModel,
    EvictTransactionCache,
    EvictWalletCache,
    RemoveTransactionReadModel,
    TrackAppliedSeq,
    UpdateTransactionReadModel,
)
from kafka_messages import TransactionCreated, TransactionDeleted, TransactionUpdated


def subscribe_transaction_created(
    router: EventRouter,
    postgres_probe: HealthProbe,
    redis_probe: HealthProbe,
):
    transaction_created = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(CreateTransactionReadModel(), TransactionCreated),
                    EvictWalletCache(TransactionCreated),
                    BumpTransactionListVersion(TransactionCreated),
                    BumpWalletListVersion(TransactionCreated),
                ]
            ),
        ]
    )
    guarded_handler = HealthGuardedHandler(
        HealthGuardedHandler(
            transaction_created,
            postgres_probe,
            guarded_errors=POSTGRES_CONNECTIVITY_ERRORS,
        ),
        redis_probe,
        guarded_errors=REDIS_CONNECTIVITY_ERRORS,
    )

    router.register("TransactionCreated", guarded_handler)


def subscribe_transaction_deleted(
    router: EventRouter,
    postgres_probe: HealthProbe,
    redis_probe: HealthProbe,
):
    transaction_deleted = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(RemoveTransactionReadModel(), TransactionDeleted),
                    EvictWalletCache(TransactionDeleted),
                    EvictTransactionCache(TransactionDeleted),
                    BumpTransactionListVersion(TransactionDeleted),
                    BumpWalletListVersion(TransactionDeleted),
                ]
            ),
        ]
    )
    guarded_handler = HealthGuardedHandler(
        HealthGuardedHandler(
            transaction_deleted,
            postgres_probe,
            guarded_errors=POSTGRES_CONNECTIVITY_ERRORS,
        ),
        redis_probe,
        guarded_errors=REDIS_CONNECTIVITY_ERRORS,
    )

    router.register("TransactionDeleted", guarded_handler)


def subscribe_transaction_updated(
    router: EventRouter,
    postgres_probe: HealthProbe,
    redis_probe: HealthProbe,
):
    transaction_updated = ExecutionPlan(
        [
            SyncProcessGroup(
                [
                    TrackAppliedSeq(UpdateTransactionReadModel(), TransactionUpdated),
                    EvictWalletCache(TransactionUpdated),
                    EvictTransactionCache(TransactionUpdated),
                    BumpTransactionListVersion(TransactionUpdated),
                    BumpWalletListVersion(TransactionUpdated),
                ]
            ),
        ]
    )
    guarded_handler = HealthGuardedHandler(
        HealthGuardedHandler(
            transaction_updated,
            postgres_probe,
            guarded_errors=POSTGRES_CONNECTIVITY_ERRORS,
        ),
        redis_probe,
        guarded_errors=REDIS_CONNECTIVITY_ERRORS,
    )

    router.register("TransactionUpdated", guarded_handler)
