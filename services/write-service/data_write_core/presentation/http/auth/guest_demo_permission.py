from rest_framework.permissions import SAFE_METHODS, BasePermission
from rest_framework.request import Request
from write_service.common.http_contract import Forbidden

from data_write_core.domain.value_objects.demo_identity import is_demo_external_id

from .gateway_user import GatewayUser

GUEST_DEMO_FORBIDDEN_MESSAGE = "Guest demo accounts cannot change this resource"


class IsNotGuestDemoAccount(BasePermission):
    def has_permission(self, request: Request, view) -> bool:
        if request.method in SAFE_METHODS:
            return True

        if isinstance(request.user, GatewayUser) and is_demo_external_id(request.user.external_id):
            raise Forbidden(GUEST_DEMO_FORBIDDEN_MESSAGE)

        return True
