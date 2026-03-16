from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request
from typing import Any

from finances.application.commands import (
    CreateWebhookEndpointCommandHandler,
    CreateWebhookEndpointCommand,
)
from finances.application.queries import (
    ListWebhooksQueryHandler,
    ListWebhooksQuery,
)
from ..pagination import StandardResultsPagination
from ..presenters import CommonHttpPresenter, MessageResultInfo, WebhookHttpPresenter
from ..serializers import CreateWebhookRequestSerializer


class WebhooksViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.creation_handler = CreateWebhookEndpointCommandHandler()
        self.list_query = ListWebhooksQueryHandler()

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
                message=f"Failed to create the new Webhook Endpoint:\n {e}"
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    def list(self, request: Request) -> Response:
        try:
            requested_hooks = self.list_query.handle(ListWebhooksQuery(
                user_id=request.user.id,
            ))

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(requested_hooks, request, view=self)
            payload = WebhookHttpPresenter.present_many(page)

            return paginator.get_paginated_response(payload)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to list the Webhook Endpoints:\n {e}"
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)