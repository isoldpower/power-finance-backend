from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request
from typing import Any

from finances.application.commands import (
    CreateWebhookEndpointCommandHandler,
    CreateWebhookEndpointCommand,
    DeleteWebhookCommand,
    DeleteWebhookCommandHandler,
    RotateWebhookSecretCommandHandler,
    RotateWebhookSecretCommand,
    UpdateWebhookEndpointCommandHandler,
    UpdateWebhookEndpointCommand,
)
from finances.application.queries import (
    ListWebhooksQueryHandler,
    ListWebhooksQuery,
    GetWebhookQueryHandler,
    GetWebhookQuery,
)

from ..pagination import StandardResultsPagination
from ..presenters import CommonHttpPresenter, MessageResultInfo, WebhookHttpPresenter
from ..serializers import (
    CreateWebhookRequestSerializer,
    UpdateWebhookRequestSerializer,
    RotateWebhookSecretRequestSerializer,
)


class WebhooksViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.list_query = ListWebhooksQueryHandler()
        self.retrieve_query = GetWebhookQueryHandler()
        self.creation_handler = CreateWebhookEndpointCommandHandler()
        self.destroy_handler = DeleteWebhookCommandHandler()
        self.rotate_handler = RotateWebhookSecretCommandHandler()
        self.update_handler = UpdateWebhookEndpointCommandHandler()

    def list(self, request: Request) -> Response:
        try:
            requested_hooks = self.list_query.handle(ListWebhooksQuery(
                user_id=request.user.id,
            ))

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(requested_hooks, request, view=self)
            payload = WebhookHttpPresenter.present_many(page)

            paginated_response = paginator.get_paginated_response(payload)
            paginated_response.status_code = status.HTTP_206_PARTIAL_CONTENT
            return paginated_response
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to list the Webhook Endpoints:\n {e}",
                resource_id=None
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request: Request, pk: str) -> Response:
        try:
            requested_hook = self.retrieve_query.handle(GetWebhookQuery(
                user_id=request.user.id,
                webhook_id=pk,
            ))

            payload = WebhookHttpPresenter.present_one(requested_hook)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to retrieve the Webhook Endpoint:\n {e}",
                resource_id=pk
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request: Request) -> Response:
        serializer = CreateWebhookRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated_data = serializer.validated_data
            result = self.creation_handler.handle(CreateWebhookEndpointCommand(
                user_id=request.user.id,
                title=validated_data.get("title"),
                url=validated_data.get("url"),
                events=validated_data.get("subscribed"),
            ))

            payload = WebhookHttpPresenter.present_one_with_secret(result)
            return Response(payload, status=status.HTTP_201_CREATED)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to create the new Webhook Endpoint:\n {e}",
                resource_id=None
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request: Request, pk: str | None = None) -> Response:
        try:
            deleted_hook = self.destroy_handler.handle(DeleteWebhookCommand(
                user_id=request.user.id,
                webhook_id=pk,
            ))

            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Successfully deleted Webhook with ID {deleted_hook.id}",
                resource_id=f"{pk}"
            ))
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to delete the Webhook Endpoint:\n {e}",
                resource_id=f"{pk}"
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        
    def partial_update(self, request: Request, pk: str | None = None) -> Response:
        serializer = UpdateWebhookRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated_data = serializer.validated_data
            result = self.update_handler.handle(UpdateWebhookEndpointCommand(
                webhook_id=pk,
                user_id=request.user.id,
                title=validated_data.get("title"),
                url=validated_data.get("url"),
                events=validated_data.get("subscribed"),
            ))

            payload = WebhookHttpPresenter.present_one(result)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to update the Webhook Endpoint:\n {e}",
                resource_id=f"{pk}"
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        
    @action(detail=True, methods=["post"], url_path="rotate")
    def rotate_secret(self, request: Request, pk: str | None = None) -> Response:
        serializer = RotateWebhookSecretRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            rotated_webhook = self.rotate_handler.handle(RotateWebhookSecretCommand(
                webhook_id=pk,
                user_id=request.user.id,
            ))

            payload = WebhookHttpPresenter.present_one_with_secret(rotated_webhook)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to rotate the Webhook Endpoint:\n {e}",
                resource_id=f"{pk}"
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)