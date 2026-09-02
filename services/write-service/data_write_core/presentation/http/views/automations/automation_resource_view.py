from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    DeleteAutomationCommand,
    DeleteAutomationCommandHandler,
    UpdateAutomationCommand,
    UpdateAutomationCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import AutomationHttpPresenter
from ...serializers import (
    EnvelopedAutomationResponseSerializer,
    ErrorResponseSerializer,
    UpdateAutomationRequestSerializer,
)
from ..mixins import CommandResponseMixin
from .base import AutomationView

AUTOMATION_ID_PARAMETER = OpenApiParameter(
    "automation_id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="Automation ID",
)


class AutomationResourceView(AutomationView, CommandResponseMixin):
    @extend_schema(
        operation_id="automations_update",
        summary="Update an automation rule",
        description=(
            "Partial update, including enabling and disabling.\n\n"
            "There is deliberately no `/toggle`: enabling is SETTING a field, "
            "and an endpoint that flips a boolean is not idempotent — two "
            "retries leave the rule where it started."
        ),
        parameters=[AUTOMATION_ID_PARAMETER],
        request=UpdateAutomationRequestSerializer,
        responses={
            200: EnvelopedAutomationResponseSerializer,
            404: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def patch(self, request, automation_id=None):
        serializer = UpdateAutomationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = serializer.validated_data

        automation, write_version = await UpdateAutomationCommandHandler().handle(
            UpdateAutomationCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                automation_id=automation_id,
                name=payload.get("name"),
                icon=payload.get("icon"),
                enabled=payload.get("enabled"),
                trigger=payload.get("trigger"),
                effects=payload.get("effects"),
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=AutomationHttpPresenter.present_one(automation),
            write_version=write_version,
        )

    @extend_schema(
        operation_id="automations_destroy",
        summary="Delete an automation rule",
        description=(
            "Soft delete. The rule stops evaluating immediately and comes back "
            "with `deleted_at` set."
        ),
        parameters=[AUTOMATION_ID_PARAMETER],
        request=None,
        responses={
            200: EnvelopedAutomationResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @trace_handler_flow
    async def delete(self, request, automation_id=None):
        automation, write_version = await DeleteAutomationCommandHandler().handle(
            DeleteAutomationCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                automation_id=automation_id,
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=AutomationHttpPresenter.present_one(automation),
            write_version=write_version,
        )
