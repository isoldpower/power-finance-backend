from data_write_core.infrastructure.repositories import (
    DjangoCurrencyRepository,
    DjangoNotificationRepository,
    DjangoOutboxRepository,
    DjangoTransactionRepository,
    DjangoUserRepository,
    DjangoWalletRepository,
    DjangoWebhookRepository,
    ImmudbMoneyFlowRepository,
)

from .state import ImmudbConnection, RepositoryRegistry


def initialize_repositories(immudb_client: ImmudbConnection) -> RepositoryRegistry:
    return RepositoryRegistry(
        wallet_repository=DjangoWalletRepository(),
        money_flow_repository=ImmudbMoneyFlowRepository(immudb_client),
        transaction_repository=DjangoTransactionRepository(),
        currency_repository=DjangoCurrencyRepository(),
        outbox_repository=DjangoOutboxRepository(),
        user_repository=DjangoUserRepository(),
        notification_repository=DjangoNotificationRepository(),
        webhook_repository=DjangoWebhookRepository(),
    )
