from drf_spectacular.utils import extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    CreateAutomationCommand,
    CreateAutomationCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import AutomationHttpPresenter
from ...serializers import (
    CreateAutomationRequestSerializer,
    EnvelopedAutomationResponseSerializer,
    ErrorResponseSerializer,
)
from ..mixins import CommandResponseMixin
from .base import AutomationView


class AutomationListView(AutomationView, CommandResponseMixin):
    @extend_schema(
        operation_id="automations_create",
        summary="Create an automation rule",
        description=(
            "WHEN something matches, DO something.\n\n"
            "`trigger.filter_body` is the SAME filter tree the `/search` "
            "endpoints take, validated against the policy of the trigger's "
            "subject: an `event` trigger against transactions, a `schedule` "
            "trigger against wallets. `null` means the rule is unconditional."
        ),
        request=CreateAutomationRequestSerializer,
        responses={
            201: EnvelopedAutomationResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def post(self, request):
        serializer = CreateAutomationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        automation, write_version = await CreateAutomationCommandHandler().handle(
            CreateAutomationCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                name=payload["name"],
                icon=payload.get("icon", ""),
                enabled=payload.get("enabled", True),
                trigger=payload["trigger"],
                effects=payload["effects"],
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_201_CREATED,
            response_body=AutomationHttpPresenter.present_one(automation),
            write_version=write_version,
        )
