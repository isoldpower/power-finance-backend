from rest_framework.routers import DefaultRouter
from django.urls import path

from .http import (
    WalletViewSet,
    TransactionViewSet,
    WebhooksViewSet,
    CategoriesAnalyticsView,
    MoneyFlowAnalyticsView,
    ExpenditureAnalyticsView,
    WalletBalanceHistoryView,
    SpendingHeatmapView,
)
from .sse import (
    notifications_stream_view,
)


# Core routes
core_router = DefaultRouter()
core_router.register(r'wallets', WalletViewSet, basename='wallet')
core_router.register(r'transactions', TransactionViewSet, basename='transaction')
core_router.register(r'webhooks', WebhooksViewSet, basename='webhook')

# Analytics routes
analytics_urls = [
    path('categories/', CategoriesAnalyticsView.as_view({'get': 'summary'}), name='category-analytics'),
    path('money-flow/', MoneyFlowAnalyticsView.as_view({'get': 'summary'}), name='money-flow-analytics'),
    path('expenditure/', ExpenditureAnalyticsView.as_view({'get': 'summary'}), name='expenditure-analytics'),
    path('spending-heatmap/', SpendingHeatmapView.as_view({'get': 'summary'}), name='spending-heatmap-analytics'),
    path('wallet-history/', WalletBalanceHistoryView.as_view({'get': 'summary'}), name='wallet-history-analytics'),
]

# General routes
general_urls = [
    path("notifications/stream", notifications_stream_view, name="notifications-stream"),
]