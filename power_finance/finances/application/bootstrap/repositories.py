from finances.infrastructure.repositories import (
    DjangoWebhookDeliveryRepository,
    DjangoWebhookRepository,
    DjangoWalletRepository,
    DjangoNotificationRepository,
    DjangoTransactionRepository,
    DjangoCurrencyRepository,
    DjangoWebhookPayloadRepository,
)
from finances.infrastructure.selectors import (
    DjangoWalletSelectorsCollection,
    DjangoTransactionSelectorsCollection,
)

from .state import RepositoryRegistry


def initialize_repositories() -> RepositoryRegistry:
    return RepositoryRegistry(
        delivery_repository=DjangoWebhookDeliveryRepository(),
        webhook_repository=DjangoWebhookRepository(),
        wallet_repository=DjangoWalletRepository(),
        notification_repository=DjangoNotificationRepository(),
        transaction_repository=DjangoTransactionRepository(),
        currency_repository=DjangoCurrencyRepository(),
        payload_repository=DjangoWebhookPayloadRepository(),
        wallet_selectors=DjangoWalletSelectorsCollection(),
        transaction_selectors=DjangoTransactionSelectorsCollection(),
    )