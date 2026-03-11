from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .presentation.http import WalletViewSet, TransactionViewSet

router = DefaultRouter()
router.register(r'wallets', WalletViewSet, basename='wallet')
router.register(r'transactions', TransactionViewSet, basename='transaction')
# router.register(r"users", UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
]
