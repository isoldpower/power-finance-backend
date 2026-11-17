from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    DeleteCategoryCommand,
    DeleteCategoryCommandHandler,
    UpdateCategoryCommand,
    UpdateCategoryCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import CategoryHttpPresenter
from ...serializers import (
    EnvelopedCategoryResponseSerializer,
    ErrorResponseSerializer,
    UpdateCategoryRequestSerializer,
)
from ..mixins import CommandResponseMixin
from .base import CategoryView
from .config import CATEGORY_ID_PARAMETER


class CategoryResourceView(CategoryView, CommandResponseMixin):
    @extend_schema(
        operation_id="categories_update",
        summary="Rename a category",
        description=(
            "Rename one of the user's own categories. Wallets and transactions that "
            "use it show the new name. Global categories cannot be renamed (409)."
        ),
        parameters=[CATEGORY_ID_PARAMETER],
        request=UpdateCategoryRequestSerializer,
        responses={
            200: EnvelopedCategoryResponseSerializer,
            404: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def patch(self, request: Request, category_id: UUID) -> Response:
        serializer = UpdateCategoryRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_category, write_version = await UpdateCategoryCommandHandler().handle(
            UpdateCategoryCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                category_id=category_id,
                name=serializer.validated_data["name"],
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=CategoryHttpPresenter.present_one(updated_category),
            write_version=write_version or None,
        )

    @extend_schema(
        operation_id="categories_delete",
        summary="Delete a category",
        description=(
            "Soft-delete one of the user's own categories. It disappears from "
            "category lists and can no longer be assigned, but wallets and "
            "transactions that already use it keep it. Global categories cannot be "
            "deleted (409)."
        ),
        parameters=[CATEGORY_ID_PARAMETER],
        responses={
            200: EnvelopedCategoryResponseSerializer,
            404: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def delete(self, request: Request, category_id: UUID) -> Response:
        deleted_category, write_version = await DeleteCategoryCommandHandler().handle(
            DeleteCategoryCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                category_id=category_id,
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=CategoryHttpPresenter.present_one(deleted_category),
            write_version=write_version,
        )
