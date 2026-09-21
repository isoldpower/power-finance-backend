from data_write_core.infrastructure.repositories import (
    DjangoActionRepository,
    DjangoAutomationRepository,
    DjangoCurrencyRepository,
    DjangoGoalRepository,
    DjangoMoneyContainerRepository,
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
        goal_repository=DjangoGoalRepository(),
        money_container_repository=DjangoMoneyContainerRepository(),
        money_flow_repository=ImmudbMoneyFlowRepository(immudb_client),
        transaction_repository=DjangoTransactionRepository(),
        currency_repository=DjangoCurrencyRepository(),
        outbox_repository=DjangoOutboxRepository(),
        user_repository=DjangoUserRepository(),
        action_repository=DjangoActionRepository(),
        automation_repository=DjangoAutomationRepository(),
        notification_repository=DjangoNotificationRepository(),
        webhook_repository=DjangoWebhookRepository(),
    )
