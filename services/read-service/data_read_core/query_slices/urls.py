from django.urls import path

from .convert_currency import convert_currency
from .count_notifications import count_notifications
from .get_account import get_account
from .get_analytics_balance_history import get_analytics_balance_history
from .get_analytics_cash_flow import get_analytics_cash_flow
from .get_analytics_categories import get_analytics_categories
from .get_analytics_category_trends import get_analytics_category_trends
from .get_analytics_dimensions import get_analytics_dimensions
from .get_analytics_money_flow import get_analytics_money_flow
from .get_analytics_overview import get_analytics_overview
from .get_analytics_spending_calendar import get_analytics_spending_calendar
from .get_analytics_spending_rhythm import get_analytics_spending_rhythm
from .get_automation import get_automation
from .get_currency_rates import get_currency_rates
from .get_goal import get_goal
from .get_metrics import get_metrics
from .get_notification import get_notification
from .get_transaction import get_transaction
from .get_wallet import get_wallet
from .get_webhook import get_webhook
from .list_accounts import list_accounts
from .list_actions import list_actions
from .list_analytics_counterparties import list_analytics_counterparties
from .list_analytics_transactions import list_analytics_transactions
from .list_automations import list_automations
from .list_categories import list_categories
from .list_currencies import list_currencies
from .list_goals import list_goals
from .list_notifications import list_notifications
from .list_transactions import list_transactions
from .list_wallets import list_wallets
from .list_webhook_event_types import list_webhook_event_types
from .list_webhook_events import list_webhook_events
from .list_webhooks import list_webhooks
from .search_automations import search_automations
from .search_goals import search_goals
from .search_transactions import search_transactions
from .search_wallets import search_wallets
from .search_webhooks import search_webhooks

urlpatterns = [
    path("actions", list_actions),
    path("analytics/dimensions", get_analytics_dimensions),
    path("analytics/overview", get_analytics_overview),
    path("analytics/cash-flow", get_analytics_cash_flow),
    path("analytics/categories", get_analytics_categories),
    path("analytics/category-trends", get_analytics_category_trends),
    path("analytics/money-flow", get_analytics_money_flow),
    path("analytics/spending-calendar", get_analytics_spending_calendar),
    path("analytics/spending-rhythm", get_analytics_spending_rhythm),
    path("analytics/balance-history", get_analytics_balance_history),
    path("analytics/counterparties", list_analytics_counterparties),
    path("analytics/transactions", list_analytics_transactions),
    path("automations", list_automations),
    path("automations/search", search_automations),
    path("automations/<uuid:automation_id>", get_automation),
    path("accounts", list_accounts),
    path("accounts/<uuid:account_id>", get_account),
    path("currencies", list_currencies),
    path("currencies/convert", convert_currency),
    path("currencies/rates/<str:code>", get_currency_rates),
    path("metrics", get_metrics),
    path("categories", list_categories),
    path("goals", list_goals),
    path("goals/search", search_goals),
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
    path("webhooks/event-types", list_webhook_event_types),
    path("webhooks/<uuid:webhook_id>", get_webhook),
    path("webhooks/<uuid:webhook_id>/events", list_webhook_events),
]
