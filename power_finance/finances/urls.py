from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .presentation.http.views.wallet_viewset import WalletViewSet

router = DefaultRouter()
router.register(r'wallets', WalletViewSet, basename='wallet')
# router.register(r'transactions', TransactionViewSet, basename='transactions')
# router.register(r"users", UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
]
