from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import UserViewSet, WalletViewSet

router = DefaultRouter()
router.register(r'wallets', WalletViewSet, basename='wallet')
router.register(r"users", UserViewSet, basename='user')

urlpatterns = [
    path('', include(router.urls)),
]
