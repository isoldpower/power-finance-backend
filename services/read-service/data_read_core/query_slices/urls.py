from django.urls import path

from .convert_currency import convert_currency
from .get_currency_rates import get_currency_rates
from .get_notification import get_notification
from .get_transaction import get_transaction
from .get_wallet import get_wallet
from .get_webhook import get_webhook
from .list_currencies import list_currencies
from .list_notifications import list_notifications
from .list_transactions import list_transactions
from .list_wallets import list_wallets
from .list_webhook_events import list_webhook_events
from .list_webhooks import list_webhooks
from .search_transactions import search_transactions
from .search_wallets import search_wallets
from .search_webhooks import search_webhooks

urlpatterns = [
    path("currencies", list_currencies),
    path("currencies/convert", convert_currency),
    path("currencies/rates/<str:code>", get_currency_rates),
    path("wallets", list_wallets),
    path("wallets/search", search_wallets),
    path("wallets/<uuid:pk>", get_wallet),
    path("transactions", list_transactions),
    path("transactions/search", search_transactions),
    path("transactions/<uuid:pk>", get_transaction),
    path("notifications", list_notifications),
    path("notifications/<uuid:pk>", get_notification),
    path("webhooks", list_webhooks),
    path("webhooks/search", search_webhooks),
    path("webhooks/<uuid:pk>", get_webhook),
    path("webhooks/<uuid:pk>/events", list_webhook_events),
]
