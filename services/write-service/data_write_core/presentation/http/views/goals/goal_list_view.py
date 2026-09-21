from drf_spectacular.utils import extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    CreateNewGoalCommand,
    CreateNewGoalCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import GoalHttpPresenter
from ...serializers import (
    CreateGoalRequestSerializer,
    EnvelopedGoalResponseSerializer,
    ErrorResponseSerializer,
)
from ..mixins import CommandResponseMixin
from .base import GoalView


class GoalListView(GoalView, CommandResponseMixin):
    @extend_schema(
        operation_id="goals_create",
        summary="Create a new goal",
        description=(
            "Create a savings goal. The goal opens empty — `progress` is derived "
            "from the transactions that touch it, so a fresh goal is always at "
            "zero. Fund it with POST /transactions/chains."
        ),
        request=CreateGoalRequestSerializer,
        responses={
            201: EnvelopedGoalResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def post(self, request):
        serializer = CreateGoalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        created_goal, write_version = await CreateNewGoalCommandHandler().handle(
            CreateNewGoalCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                name=validated["name"],
                currency=validated["currency"],
                target=validated["target"],
                finish_at=validated.get("finish_at"),
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_201_CREATED,
            response_body=await GoalHttpPresenter.present_one(created_goal),
            write_version=write_version,
        )
