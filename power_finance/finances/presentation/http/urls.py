from rest_framework.routers import DefaultRouter

from .views import (
    WalletViewSet,
    TransactionViewSet,
    WebhooksViewSet,
    CategoriesAnalyticsView,
    MoneyFlowAnalyticsView,
    ExpenditureAnalyticsView,
    WalletBalanceHistoryView,
    SpendingHeatmapView,
)


# Core routes
core_router = DefaultRouter()
core_router.register(r'wallets', WalletViewSet, basename='wallet')
core_router.register(r'transactions', TransactionViewSet, basename='transaction')
core_router.register(r'webhooks', WebhooksViewSet, basename='webhook')
# Analytics routes
analytics_router = DefaultRouter()
analytics_router.register(r'wallet-history', WalletBalanceHistoryView, basename='wallet-history-analytics')

from django.urls import path

analytics_urls = [
    path('categories/', CategoriesAnalyticsView.as_view({'get': 'summary'}), name='category-analytics'),
    path('money-flow/', MoneyFlowAnalyticsView.as_view({'get': 'summary'}), name='money-flow-analytics'),
    path('expenditure/', ExpenditureAnalyticsView.as_view({'get': 'summary'}), name='expenditure-analytics'),
    path('spending-heatmap/', SpendingHeatmapView.as_view({'get': 'summary'}), name='spending-heatmap-analytics'),
]