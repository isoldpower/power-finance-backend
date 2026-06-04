from django.urls import path

from .views.fallback_read import (
    FallbackTransactionListView,
    FallbackTransactionResourceView,
    FallbackWalletListView,
    FallbackWalletResourceView,
)
from .views.transactions import TransactionListView, TransactionResourceView
from .views.wallets import WalletListView, WalletResourceView

urlpatterns = [
    path(
        "transactions/",
        TransactionListView.as_view(),
        name="transactions-list",
    ),
    path(
        "transactions/<uuid:pk>/",
        TransactionResourceView.as_view(),
        name="transactions-resource",
    ),
    path(
        "wallets/",
        WalletListView.as_view(),
        name="wallets-list",
    ),
    path(
        "wallets/<uuid:pk>/",
        WalletResourceView.as_view(),
        name="wallets-resource",
    ),
    # Always-consistent fallback reads. The gateway redirects here when the
    # Read Service returns 507 (projection behind the client's Read-At-Least).
    path(
        "fallback-reads/wallets/",
        FallbackWalletListView.as_view(),
        name="fallback-wallets-list",
    ),
    path(
        "fallback-reads/wallets/<uuid:pk>/",
        FallbackWalletResourceView.as_view(),
        name="fallback-wallets-resource",
    ),
    path(
        "fallback-reads/transactions/",
        FallbackTransactionListView.as_view(),
        name="fallback-transactions-list",
    ),
    path(
        "fallback-reads/transactions/<uuid:pk>/",
        FallbackTransactionResourceView.as_view(),
        name="fallback-transactions-resource",
    ),
]
