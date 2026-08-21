from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from .gateway_user import GatewayUser


class IsGatewayAuthenticated(BasePermission):
    def has_permission(self, request: Request, view) -> bool:
        return isinstance(request.user, GatewayUser)
