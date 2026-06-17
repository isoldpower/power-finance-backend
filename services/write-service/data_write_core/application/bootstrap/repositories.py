from data_write_core.infrastructure.repositories import (
    DjangoCurrencyRepository,
    DjangoNotificationRepository,
    DjangoOutboxRepository,
    DjangoUserRepository,
    DjangoWalletRepository,
    DjangoWebhookRepository,
    ImmudbTransactionRepository,
)

from .state import ImmudbConnection, RepositoryRegistry


def initialize_repositories(immudb_client: ImmudbConnection) -> RepositoryRegistry:
    return RepositoryRegistry(
        wallet_repository=DjangoWalletRepository(),
        transaction_repository=ImmudbTransactionRepository(immudb_client),
        currency_repository=DjangoCurrencyRepository(),
        outbox_repository=DjangoOutboxRepository(),
        user_repository=DjangoUserRepository(),
        notification_repository=DjangoNotificationRepository(),
        webhook_repository=DjangoWebhookRepository(),
    )
