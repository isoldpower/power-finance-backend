from django.urls import path

from .views import (
    MoneyFlowAnalyticsView,
)

urlpatterns = [
    path("money-flow/", MoneyFlowAnalyticsView.as_view()),
]