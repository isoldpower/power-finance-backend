from data_write_core.infrastructure.repositories import (
    DjangoCurrencyRepository,
    DjangoWalletRepository,
    ImmudbTransactionRepository,
)

from .state import ImmudbConnection, RepositoryRegistry


def initialize_repositories(immudb_client: ImmudbConnection) -> RepositoryRegistry:
    return RepositoryRegistry(
        wallet_repository=DjangoWalletRepository(),
        transaction_repository=ImmudbTransactionRepository(immudb_client),
        currency_repository=DjangoCurrencyRepository(),
    )
