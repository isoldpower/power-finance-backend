from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from write_service.common.base_async_api_view import BaseAsyncAPIView
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    ResolveActionCommand,
    ResolveActionCommandHandler,
)

from ...auth import IsGatewayAuthenticated
from ...decorators import trace_handler_flow
from ...presenters import ActionHttpPresenter
from ...serializers import (
    EnvelopedActionResponseSerializer,
    ErrorResponseSerializer,
    ResolveActionRequestSerializer,
)
from ..mixins import CommandResponseMixin


class ActionResolveView(BaseAsyncAPIView, CommandResponseMixin):
    permission_classes = [IsGatewayAuthenticated]

    @extend_schema(
        operation_id="actions_resolve",
        summary="Answer an action",
        description=(
            "Choose one of the action's offered resolutions.\n\n"
            "Choosing one whose `applies` was true performs the described "
            "change to other resources as part of the same request, and the "
            "response then carries `X-Write-Version` so you can send "
            "`Read-At-Least` on the follow-up read. When `applies` was false "
            "nothing outside the action changes and no write version is "
            "emitted.\n\n"
            "`resolutions` comes back EMPTY: a resolved action offers no "
            "further choices, and an empty array rather than a stale list is "
            "what stops a client re-rendering buttons that no longer work.\n\n"
            "Answering is terminal — a second answer is 409 "
            "`action_already_resolved`. `Idempotency-Key` is optional but "
            "recommended for resolutions that apply, since those move real data."
        ),
        parameters=[
            OpenApiParameter(
                "action_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Action ID",
            ),
        ],
        request=ResolveActionRequestSerializer,
        responses={
            200: EnvelopedActionResponseSerializer,
            404: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def post(self, request, action_id=None):
        serializer = ResolveActionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        resolved, write_version = await ResolveActionCommandHandler().handle(
            ResolveActionCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                action_id=action_id,
                resolution_id=serializer.validated_data["resolution_id"],
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=ActionHttpPresenter.present_one(resolved.action),
            # Only when the choice actually moved something outside the action:
            # a version the client cannot use would invite a `Read-At-Least` on
            # a read that was never going to change.
            write_version=write_version if resolved.applies else None,
        )
