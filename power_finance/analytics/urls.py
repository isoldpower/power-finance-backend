from django.urls import path

from .views import (
    CategoriesAnalyticsView,
    MoneyFlowAnalyticsView,
    ExpenditureAnalyticsView,
    WalletBalanceHistoryView,
    SpendingHeatmapView
)

urlpatterns = [
    path("categories/", CategoriesAnalyticsView.as_view()),
    path("money-flow/", MoneyFlowAnalyticsView.as_view()),
    path("expenditure/", ExpenditureAnalyticsView.as_view()),
    path("wallet-history/<uuid:wallet_id>/", WalletBalanceHistoryView.as_view()),
    path("spending-heatmap/", SpendingHeatmapView.as_view()),
]