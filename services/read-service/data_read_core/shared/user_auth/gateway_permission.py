from rest_framework.permissions import BasePermission
from rest_framework.request import Request


class IsGatewayAuthenticated(BasePermission):
    def has_permission(self, request: Request, view) -> bool:
        return bool(request.user and request.user.is_authenticated)
