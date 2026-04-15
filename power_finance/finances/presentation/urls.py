from django.urls import path

from .http import (
    WalletListView,
    WalletSearchView,
    WalletResourceView,
    TransactionListView,
    TransactionSearchView,
    TransactionResourceView,
    CategoriesAnalyticsView,
    MoneyFlowAnalyticsView,
    ExpenditureAnalyticsView,
    WalletBalanceHistoryView,
    SpendingHeatmapView,
    NotificationListView,
    NotificationBatchAckView,
    NotificationAckView,
    notification_stream,
    WebhookListView,
    WebhookSearchView,
    WebhookResourceView,
    WebhookEventListView,
    WebhookEventResourceView,
    WebhookSecretView,
)

# Wallet routes (APIView — explicit paths, not router)
wallet_urls = [
    path('wallets/', WalletListView.as_view(), name='wallet-list'),
    path('wallets/search/', WalletSearchView.as_view(), name='wallet-search'),
    path('wallets/<uuid:pk>/', WalletResourceView.as_view(), name='wallet-detail'),
]

# Transaction routes (APIView - explicit paths, not router)
transaction_urls = [
    path('transactions/', TransactionListView.as_view(), name='transaction-list'),
    path('transactions/search/', TransactionSearchView.as_view(), name='transaction-search'),
    path('transactions/<uuid:pk>/', TransactionResourceView.as_view(), name='transaction-detail'),
]

# Analytics routes (APIView - explicit paths, not router)
analytics_urls = [
    path('categories/', CategoriesAnalyticsView.as_view(), name='category-analytics'),
    path('money-flow/', MoneyFlowAnalyticsView.as_view(), name='money-flow-analytics'),
    path('expenditure/', ExpenditureAnalyticsView.as_view(), name='expenditure-analytics'),
    path('spending-heatmap/', SpendingHeatmapView.as_view(), name='spending-heatmap-analytics'),
    path('wallet-history/<uuid:pk>/', WalletBalanceHistoryView.as_view(), name='wallet-history-analytics'),
]

# Webhook routes (APIView - explicit paths, not router)
webhooks_urls = [
    path('webhooks/', WebhookListView.as_view(), name='transaction-list'),
    path('webhooks/search/', WebhookSearchView.as_view(), name='transaction-search'),
    path('webhooks/<uuid:pk>/', WebhookResourceView.as_view(), name='transaction-detail'),
    path('webhooks/<uuid:pk>/events/', WebhookEventListView.as_view(), name='webhook-event-list'),
    path('webhooks/<uuid:pk>/events/<uuid:subscription_id>/', WebhookEventResourceView.as_view(), name='webhook-event-detail'),
    path('webhooks/<uuid:pk>/secret/', WebhookSecretView.as_view(), name='webhook-secret'),
]

# Notification routes (APIView — explicit paths, not router)
notification_urls = [
    path('notifications/', NotificationListView.as_view(), name='notification-list'),
    path('notifications/ack/', NotificationBatchAckView.as_view(), name='notification-batch-ack'),
    path('notifications/<uuid:notification_id>/ack/', NotificationAckView.as_view(), name='notification-ack'),
    path('notifications/stream/', notification_stream, name='notification-stream'),
]

# General routes
general_urls = []