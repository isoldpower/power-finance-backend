from django.urls import path

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
]
