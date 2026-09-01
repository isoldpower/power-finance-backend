from django.urls import path

from .convert_currency import convert_currency
from .count_notifications import count_notifications
from .get_account import get_account
from .get_currency_rates import get_currency_rates
from .get_goal import get_goal
from .get_metrics import get_metrics
from .get_notification import get_notification
from .get_transaction import get_transaction
from .get_wallet import get_wallet
from .get_webhook import get_webhook
from .list_accounts import list_accounts
from .list_currencies import list_currencies
from .list_goals import list_goals
from .list_notifications import list_notifications
from .list_transactions import list_transactions
from .list_wallets import list_wallets
from .list_webhook_events import list_webhook_events
from .list_webhooks import list_webhooks
from .search_transactions import search_transactions
from .search_wallets import search_wallets
from .search_webhooks import search_webhooks

urlpatterns = [
    path("accounts", list_accounts),
    path("accounts/<uuid:account_id>", get_account),
    path("currencies", list_currencies),
    path("currencies/convert", convert_currency),
    path("currencies/rates/<str:code>", get_currency_rates),
    path("metrics", get_metrics),
    path("goals", list_goals),
    path("goals/<uuid:goal_id>", get_goal),
    path("wallets", list_wallets),
    path("wallets/search", search_wallets),
    path("wallets/<uuid:wallet_id>", get_wallet),
    path("transactions", list_transactions),
    path("transactions/search", search_transactions),
    path("transactions/<uuid:transaction_id>", get_transaction),
    path("notifications", list_notifications),
    path("notifications/count", count_notifications),
    path("notifications/<uuid:notification_id>", get_notification),
    path("webhooks", list_webhooks),
    path("webhooks/search", search_webhooks),
    path("webhooks/<uuid:webhook_id>", get_webhook),
    path("webhooks/<uuid:webhook_id>/events", list_webhook_events),
]
