from django.urls import path

from .get_transaction import get_transaction
from .get_wallet import get_wallet
from .list_transactions import list_transactions
from .list_wallets import list_wallets

urlpatterns = [
    path("wallets/", list_wallets),
    path("wallets/<uuid:pk>/", get_wallet),
    path("transactions/", list_transactions),
    path("transactions/<uuid:pk>/", get_transaction),
]
