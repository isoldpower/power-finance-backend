from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    SoftDeleteGoalCommand,
    SoftDeleteGoalCommandHandler,
    UpdateExistingGoalCommand,
    UpdateExistingGoalCommandHandler,
)
from data_write_core.domain.entities.goal import UNCHANGED

from ...decorators import trace_handler_flow
from ...presenters import GoalHttpPresenter
from ...serializers import (
    EnvelopedGoalResponseSerializer,
    ErrorResponseSerializer,
    UpdateGoalRequestSerializer,
)
from ..mixins import CommandResponseMixin
from .base import GoalView

GOAL_ID_PARAMETER = OpenApiParameter(
    "id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="Goal ID",
)


class GoalResourceView(GoalView, CommandResponseMixin):
    @extend_schema(
        operation_id="goals_partial_update",
        summary="Update a goal",
        description=(
            "Partial update of a goal's client-managed metadata. An omitted field "
            "is left alone. `currency` is fixed at creation and is not accepted; "
            "`progress` is derived and is ignored if sent."
        ),
        parameters=[GOAL_ID_PARAMETER],
        request=UpdateGoalRequestSerializer,
        responses={
            200: EnvelopedGoalResponseSerializer,
            404: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def patch(self, request, goal_id=None):
        serializer = UpdateGoalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        updated_goal, write_version = await UpdateExistingGoalCommandHandler().handle(
            UpdateExistingGoalCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                goal_id=goal_id,
                new_name=validated.get("name", UNCHANGED),
                target=validated.get("target", UNCHANGED),
                finish_at=validated.get("finish_at", UNCHANGED),
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=await GoalHttpPresenter.present_one(updated_goal),
            write_version=write_version,
        )

    @extend_schema(
        operation_id="goals_delete",
        summary="Close a goal",
        description=(
            "Closes the goal (sets deleted_at). The row is preserved so the "
            "transactions that touched it remain queryable, but the goal leaves "
            "lists. Only an empty goal closes: `progress` must be zero, otherwise "
            "409 `goal_not_empty` — drain it with a transfer chain first. "
            "Repeating the call is a no-op that returns the same body."
        ),
        parameters=[GOAL_ID_PARAMETER],
        responses={
            200: EnvelopedGoalResponseSerializer,
            404: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def delete(self, request, goal_id=None):
        deleted_goal, write_version = await SoftDeleteGoalCommandHandler().handle(
            SoftDeleteGoalCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                goal_id=goal_id,
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=await GoalHttpPresenter.present_one(deleted_goal),
            write_version=write_version,
        )
