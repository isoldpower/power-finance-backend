import logging
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from typing import Any

from environment.presentation.http.base_api_view import BaseAPIView
from environment.presentation.middleware import WebhookRegistrationThrottle
from finances.application.use_cases import (
    CreateWebhookEndpointCommandHandler,
    CreateWebhookEndpointCommand,
    DeleteWebhookCommand,
    DeleteWebhookCommandHandler,
    RotateWebhookSecretCommandHandler,
    RotateWebhookSecretCommand,
    UpdateWebhookEndpointCommandHandler,
    UpdateWebhookEndpointCommand,
    SubscribeToEventCommandHandler,
    SubscribeToEventCommand,
    UnsubscribeFromEventCommandHandler,
    UnsubscribeFromEventCommand,
    ListFilteredWebhooksQuery,
    ListFilteredWebhooksQueryHandler,
)
from finances.application.use_cases import (
    ListWebhooksQueryHandler,
    ListWebhooksQuery,
    GetWebhookQueryHandler,
    GetWebhookQuery,
    GetWebhookSubscriptionsQueryHandler,
    GetWebhookSubscriptionsQuery,
)
from finances.domain.exceptions import FilterParseError

from ..pagination import StandardResultsPagination
from ..presenters import CommonHttpPresenter, MessageResultInfo, WebhookHttpPresenter
from ..serializers import (
    CreateWebhookRequestSerializer,
    UpdateWebhookRequestSerializer,
    RotateWebhookSecretRequestSerializer,
    SubscribeWebhookToEventRequestSerializer,
    WebhookResponseSerializer,
    WebhookWithSecretResponseSerializer,
    WebhookSimpleResponseSerializer,
    WebhookSubscriptionResponseSerializer,
    MessageResponseSerializer,
    FilterWebhooksRequestSerializer,
)

logger = logging.getLogger(__name__)


class WebhooksViewSet(viewsets.ViewSet, BaseAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [WebhookRegistrationThrottle]
    pagination_class = StandardResultsPagination

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        self.list_query = ListWebhooksQueryHandler()
        self.retrieve_query = GetWebhookQueryHandler()
        self.creation_handler = CreateWebhookEndpointCommandHandler()
        self.destroy_handler = DeleteWebhookCommandHandler()
        self.rotate_handler = RotateWebhookSecretCommandHandler()
        self.update_handler = UpdateWebhookEndpointCommandHandler()
        self.subscribe_handler = SubscribeToEventCommandHandler()
        self.unsubscribe_handler = UnsubscribeFromEventCommandHandler()
        self.list_events_query = GetWebhookSubscriptionsQueryHandler()
        self.list_filtered_query = ListFilteredWebhooksQueryHandler()

    @extend_schema(
        operation_id="webhooks_list",
        summary="List webhooks",
        description="Retrieve a paginated list of your webhook endpoints.",
        responses={
            206: WebhookSimpleResponseSerializer(many=True),
            400: MessageResponseSerializer
        }
    )
    def list(self, request: Request) -> Response:
        logger.info("WebhooksViewSet: Received request to list webhooks for User ID: %s", request.user.id)
        try:
            requested_hooks = self.list_query.handle(ListWebhooksQuery(
                user_id=request.user.id,
            ))

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(requested_hooks, request, view=self)
            payload = WebhookHttpPresenter.present_many(page)

            paginated_response = paginator.get_paginated_response(payload)
            paginated_response.status_code = status.HTTP_206_PARTIAL_CONTENT
            logger.info("WebhooksViewSet: Successfully listed %d webhooks for User ID: %s", len(page) if page else 0, request.user.id)
            return paginated_response
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to list the Webhook Endpoints:\n {e}",
                resource_id=None
            ))

            logger.error("WebhooksViewSet: Failed to list webhooks for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="webhooks_retrieve",
        summary="Get webhook details",
        description="Retrieve detailed information about a specific webhook endpoint.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Webhook ID"
            )
        ],
        responses={
            200: WebhookResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    def retrieve(self, request: Request, pk: str) -> Response:
        try:
            logger.info("WebhooksViewSet: Received request to retrieve Webhook ID: %s for User ID: %s", pk, request.user.id)
            requested_hook = self.retrieve_query.handle(GetWebhookQuery(
                user_id=request.user.id,
                webhook_id=pk,
            ))
            payload = WebhookHttpPresenter.present_one(requested_hook)

            logger.info("WebhooksViewSet: Successfully retrieved Webhook ID: %s for User ID: %s", pk, request.user.id)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to retrieve the Webhook Endpoint:\n {e}",
                resource_id=pk
            ))

            logger.error("WebhooksViewSet: Failed to retrieve Webhook ID: %s for User ID: %s - %s", pk, request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="webhooks_create",
        summary="Create a new webhook",
        description="Register a new webhook endpoint. The secret will be returned only once.",
        request=CreateWebhookRequestSerializer,
        responses={
            201: WebhookWithSecretResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    def create(self, request: Request) -> Response:
        logger.info("WebhooksViewSet: Received request to create new webhook for User ID: %s", request.user.id)
        serializer = CreateWebhookRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated_data = serializer.validated_data
            result = self.creation_handler.handle(CreateWebhookEndpointCommand(
                user_id=request.user.id,
                title=validated_data.get("title"),
                url=validated_data.get("url"),
            ))
            payload = WebhookHttpPresenter.present_one_with_secret(result)

            logger.info("WebhooksViewSet: Successfully created new Webhook ID: %s for User ID: %s", result.id, request.user.id)
            return Response(payload, status=status.HTTP_201_CREATED)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to create the new Webhook Endpoint:\n {e}",
                resource_id=None
            ))

            logger.error("WebhooksViewSet: Failed to create new webhook for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="webhooks_delete",
        summary="Delete a webhook",
        description="Delete a specific webhook endpoint.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Webhook ID"
            )
        ],
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    def destroy(self, request: Request, pk: str | None = None) -> Response:
        logger.info("WebhooksViewSet: Received request to delete Webhook ID: %s for User ID: %s", pk, request.user.id)
        try:
            deleted_hook = self.destroy_handler.handle(DeleteWebhookCommand(
                user_id=request.user.id,
                webhook_id=pk,
            ))
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Successfully deleted Webhook with ID {deleted_hook.id}",
                resource_id=f"{pk}"
            ))

            logger.info("WebhooksViewSet: Successfully deleted Webhook ID: %s for User ID: %s", pk, request.user.id)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to delete the Webhook Endpoint:\n {e}",
                resource_id=f"{pk}"
            ))

            logger.error("WebhooksViewSet: Failed to delete Webhook ID: %s for User ID: %s - %s", pk, request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="webhooks_partial_update",
        summary="Update a webhook",
        description="Update the title or URL of an existing webhook endpoint.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Webhook ID"
            )
        ],
        request=UpdateWebhookRequestSerializer,
        responses={
            200: WebhookResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    def partial_update(self, request: Request, pk: str | None = None) -> Response:
        logger.info("WebhooksViewSet: Received request to update Webhook ID: %s for User ID: %s", pk, request.user.id)
        serializer = UpdateWebhookRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated_data = serializer.validated_data
            result = self.update_handler.handle(UpdateWebhookEndpointCommand(
                webhook_id=pk,
                user_id=request.user.id,
                title=validated_data.get("title"),
                url=validated_data.get("url"),
            ))
            payload = WebhookHttpPresenter.present_one(result)

            logger.info("WebhooksViewSet: Successfully updated Webhook ID: %s for User ID: %s", pk, request.user.id)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to update the Webhook Endpoint:\n {e}",
                resource_id=f"{pk}"
            ))

            logger.error("WebhooksViewSet: Failed to update Webhook ID: %s for User ID: %s - %s", pk, request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        
    @extend_schema(
        operation_id="webhooks_rotate_secret",
        summary="Rotate webhook secret",
        description="Rotate the signing secret for this webhook endpoint.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Webhook ID"
            )
        ],
        request=RotateWebhookSecretRequestSerializer,
        responses={
            200: WebhookWithSecretResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    @action(detail=True, methods=["post"], url_path="rotate")
    def rotate_secret(self, request: Request, pk: str | None = None) -> Response:
        logger.info("WebhooksViewSet: Received request to rotate secret for Webhook ID: %s for User ID: %s", pk, request.user.id)
        serializer = RotateWebhookSecretRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            rotated_webhook = self.rotate_handler.handle(RotateWebhookSecretCommand(
                webhook_id=pk,
                user_id=request.user.id,
            ))
            payload = WebhookHttpPresenter.present_one_with_secret(rotated_webhook)

            logger.info("WebhooksViewSet: Successfully rotated secret for Webhook ID: %s for User ID: %s", pk, request.user.id)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to rotate the Webhook Endpoint:\n {e}",
                resource_id=f"{pk}"
            ))

            logger.error("WebhooksViewSet: Failed to rotate secret for Webhook ID: %s for User ID: %s - %s", pk, request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        methods=["POST"],
        operation_id="webhooks_search",
        summary="Search webhooks with filters",
        description="Retrieve a list of webhooks by applying a filter tree passed in the request body. "
                    "Supports complex logic with 'and'/'or' groups and various field operators.",
        request=FilterWebhooksRequestSerializer,
        responses={
            200: WebhookSimpleResponseSerializer(many=True),
            400: MessageResponseSerializer,
            500: MessageResponseSerializer
        }
    )
    @action(detail=False, methods=["post"], url_path="search")
    def search_filtered_webhooks(
            self,
            request: Request
    ) -> Response:
        logger.info("WebhooksViewSet: Received request to search filtered webhooks for User ID: %s", request.user.id)
        serializer = FilterWebhooksRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated_data = serializer.validated_data
            filtered_webhooks = self.list_filtered_query.handle(ListFilteredWebhooksQuery(
                user_id=request.user.id,
                filter_body=validated_data.get("filter_body"),
            ))

            paginator = self.pagination_class()
            paginated_response = paginator.paginate_queryset(filtered_webhooks, request, view=self)
            payload = WebhookHttpPresenter.present_many(paginated_response)

            logger.info("WebhooksViewSet: Successfully retrieved %d filtered webhooks for User ID: %s", len(paginated_response) if paginated_response else 0, request.user.id)
            return paginator.get_paginated_response(payload)
        except FilterParseError as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Error occurred while resolving the passed filtration tree:\n {e}",
                resource_id=None
            ))

            logger.error("WebhooksViewSet: Failed to parse filters for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to get filtered webhooks with passed filters:\n {e}",
                resource_id=None
            ))

            logger.error("WebhooksViewSet: Failed to get filtered webhooks for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        methods=["POST"],
        operation_id="webhooks_subscribe",
        summary="Subscribe to event",
        description="Subscribe a webhook to a specific event type.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Webhook ID"
            )
        ],
        request=SubscribeWebhookToEventRequestSerializer,
        responses={
            201: WebhookSubscriptionResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    @extend_schema(
        methods=["GET"],
        operation_id="webhooks_list_subscriptions",
        summary="List event subscriptions",
        description="List all active event subscriptions for a specific webhook.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Webhook ID"
            )
        ],
        responses={
            200: WebhookSubscriptionResponseSerializer(many=True),
            400: MessageResponseSerializer
        }
    )
    @action(detail=True, methods=["get", "post"], url_path="events")
    def events(
            self,
            request: Request,
            pk: str | None = None
    ) -> Response:
        if request.method == "POST":
            return self._subscribe_to_event(request, pk)
        else:
            return self._list_events(request, pk)

    def _list_events(self, request: Request, pk: str | None) -> Response:
        try:
            logger.info("WebhooksViewSet: Received request to list event subscriptions for Webhook ID: %s for User ID: %s", pk, request.user.id)
            subscriptions = self.list_events_query.handle(GetWebhookSubscriptionsQuery(
                webhook_id=pk,
                user_id=request.user.id,
            ))

            paginator = self.pagination_class()
            paginated_response = paginator.paginate_queryset(subscriptions, request, view=self)
            payload = WebhookHttpPresenter.present_subscription_list(paginated_response)

            logger.info("WebhooksViewSet: Successfully listed %d event subscriptions for Webhook ID: %s for User ID: %s", len(paginated_response) if paginated_response else 0, pk, request.user.id)
            return paginator.get_paginated_response(payload)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to list event subscriptions:\n {e}",
                resource_id=pk
            ))

            logger.error("WebhooksViewSet: Failed to list event subscriptions for Webhook ID: %s for User ID: %s - %s", pk, request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    def _subscribe_to_event(self, request: Request, pk: str | None) -> Response:
        logger.info("WebhooksViewSet: Received request to subscribe Webhook ID: %s to event for User ID: %s", pk, request.user.id)
        serializer = SubscribeWebhookToEventRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            subscription = self.subscribe_handler.handle(SubscribeToEventCommand(
                webhook_id=pk,
                user_id=request.user.id,
                event_type=serializer.validated_data.get("event_type"),
            ))
            payload = WebhookHttpPresenter.present_subscription(subscription)

            logger.info("WebhooksViewSet: Successfully subscribed Webhook ID: %s to event %s for User ID: %s", pk, subscription.type, request.user.id)
            return Response(payload, status=status.HTTP_201_CREATED)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to subscribe to event:\n {e}",
                resource_id=pk
            ))

            logger.error("WebhooksViewSet: Failed to subscribe Webhook ID: %s to event for User ID: %s - %s", pk, request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="webhooks_unsubscribe",
        summary="Unsubscribe from event",
        description="Remove an event subscription from a webhook.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Webhook ID"
            ),
            OpenApiParameter(
                'subscription_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Subscription ID"
            )
        ],
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    @action(detail=True, methods=["delete"], url_path=r"events/(?P<subscription_id>[^/.]+)")
    def unsubscribe_from_event(
            self,
            request: Request,
            pk: str | None = None,
            subscription_id: str | None = None
    ) -> Response:
        logger.info("WebhooksViewSet: Received request to unsubscribe Webhook ID: %s from event subscription ID: %s for User ID: %s", pk, subscription_id, request.user.id)
        try:
            self.unsubscribe_handler.handle(UnsubscribeFromEventCommand(
                subscription_id=subscription_id,
                webhook_id=pk,
                user_id=request.user.id,
            ))
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Successfully unsubscribed from event with subscription ID {subscription_id}",
                resource_id=subscription_id
            ))

            logger.info("WebhooksViewSet: Successfully unsubscribed Webhook ID: %s from event subscription ID: %s for User ID: %s", pk, subscription_id, request.user.id)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to unsubscribe from event:\n {e}",
                resource_id=subscription_id
            ))

            logger.error("WebhooksViewSet: Failed to unsubscribe Webhook ID: %s from event subscription ID: %s for User ID: %s - %s", pk, subscription_id, request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)