from finances.infrastructure.repositories import (
    DjangoWebhookDeliveryRepository,
    DjangoWebhookRepository,
    DjangoWalletRepository,
    DjangoNotificationRepository,
    ImmudbTransactionRepository,
    DjangoCurrencyRepository,
    DjangoWebhookPayloadRepository,
)
from finances.infrastructure.selectors import (
    DjangoWalletSelectorsCollection,
    ImmudbTransactionSelectorsCollection,
)

from .state import ImmudbConnection, RepositoryRegistry


def initialize_repositories(immudb_client: ImmudbConnection) -> RepositoryRegistry:
    return RepositoryRegistry(
        delivery_repository=DjangoWebhookDeliveryRepository(),
        webhook_repository=DjangoWebhookRepository(),
        wallet_repository=DjangoWalletRepository(),
        notification_repository=DjangoNotificationRepository(),
        transaction_repository=ImmudbTransactionRepository(immudb_client),
        currency_repository=DjangoCurrencyRepository(),
        payload_repository=DjangoWebhookPayloadRepository(),
        wallet_selectors=DjangoWalletSelectorsCollection(),
        transaction_selectors=ImmudbTransactionSelectorsCollection(immudb_client),
    )