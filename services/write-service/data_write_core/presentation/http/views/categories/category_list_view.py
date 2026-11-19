from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    CreateCategoryCommand,
    CreateCategoryCommandHandler,
)
from data_write_core.domain.value_objects import CategoryKind

from ...decorators import trace_handler_flow
from ...presenters import CategoryHttpPresenter
from ...serializers import (
    CreateCategoryRequestSerializer,
    EnvelopedCategoryResponseSerializer,
    ErrorResponseSerializer,
)
from ..mixins import CommandResponseMixin
from .base import CategoryView


class CategoryListView(CategoryView, CommandResponseMixin):
    @extend_schema(
        operation_id="categories_create",
        summary="Create a category",
        description=(
            "Create a user-owned category for transactions or wallets. Names are "
            "unique per kind, case-insensitively, across the user's own categories "
            "and the global ones every user sees."
        ),
        request=CreateCategoryRequestSerializer,
        responses={
            201: EnvelopedCategoryResponseSerializer,
            409: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=True)
    @trace_handler_flow
    async def post(self, request: Request) -> Response:
        serializer = CreateCategoryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        created_category, write_version = await CreateCategoryCommandHandler().handle(
            CreateCategoryCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                kind=CategoryKind(validated["kind"]),
                name=validated["name"],
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_201_CREATED,
            response_body=CategoryHttpPresenter.present_one(created_category),
            write_version=write_version,
        )
