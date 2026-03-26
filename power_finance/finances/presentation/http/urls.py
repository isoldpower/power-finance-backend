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
analytics_router.register(r'categories', CategoriesAnalyticsView, basename='category-analytics')
analytics_router.register(r'money-flow', MoneyFlowAnalyticsView, basename='money-flow-analytics')
analytics_router.register(r'expenditure', ExpenditureAnalyticsView, basename='expenditure-analytics')
analytics_router.register(r'spending-heatmap', SpendingHeatmapView, basename='spending-heatmap-analytics')
analytics_router.register(r'wallet-history', WalletBalanceHistoryView, basename='wallet-history-analytics')