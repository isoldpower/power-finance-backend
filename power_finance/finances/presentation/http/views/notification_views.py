import logging
from django.http import StreamingHttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from identity.authentication import ClerkJWTAuthentication
from identity.presentation.auth_decorators import async_with_auth

from finances.application.bootstrap import application
from finances.application.use_cases import (
    AcknowledgeNotificationCommand,
    AcknowledgeNotificationCommandHandler,
    OpenNotificationsConnectionHandler,
    OpenNotificationsConnection,
    BatchAcknowledgeNotificationCommand,
    BatchAcknowledgeNotificationCommandHandler,
    ListNotificationsQuery,
    ListNotificationsQueryHandler,
)

from ..presenters import (
    CommonHttpPresenter,
    MessageResultInfo,
    NotificationHttpPresenter,
)
from ..serializers import (
    MessageResponseSerializer,
    BatchAcknowledgeRequestSerializer,
    NotificationResponseSerializer,
)
from ..pagination import StandardResultsPagination

logger = logging.getLogger(__name__)


class NotificationViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination

    @extend_schema(
        operation_id="notifications_list",
        summary="List notifications",
        description="Retrieve a paginated list of your notifications.",
        responses={
            200: NotificationResponseSerializer(many=True),
            400: MessageResponseSerializer
        }
    )
    def list(self, request):
        logger.info("NotificationViewSet: Received request to list notifications for User ID: %s", request.user.id)
        try:
            handler = ListNotificationsQueryHandler()
            notifications = handler.handle(ListNotificationsQuery(
                user_id=request.user.id
            ))

            paginator = self.pagination_class()
            queryset_page = paginator.paginate_queryset(notifications, request)
            payload = NotificationHttpPresenter.present_many(queryset_page)

            logger.info("NotificationViewSet: Successfully listed %d notifications for User ID: %s", len(queryset_page) if queryset_page else 0, request.user.id)
            return paginator.get_paginated_response(payload)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to list notifications: {e}",
                resource_id=None
            ))

            logger.error("NotificationViewSet: Failed to list notifications for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        methods=["POST"],
        operation_id="notifications_acknowledge",
        summary="Acknowledge notification",
        description="Acknowledge receipt of a notification, marking it as delivered. This stops the SSE stream from sending it again.",
        parameters=[
            OpenApiParameter(
                'notification_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Notification ID"
            )
        ],
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer,
            403: MessageResponseSerializer,
            404: MessageResponseSerializer,
        }
    )
    @action(detail=False, methods=["post"], url_path="(?P<notification_id>[^/.]+)/ack")
    def acknowledge(self, request, notification_id=None):
        logger.info("NotificationViewSet: Received request to acknowledge Notification ID: %s for User ID: %s", notification_id, request.user.id)
        try:
            handler = AcknowledgeNotificationCommandHandler()
            notification = handler.handle(AcknowledgeNotificationCommand(
                user_id=request.user.id,
                notification_id=notification_id,
            ))

            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Acknowledged notification with ID {notification.id}",
                resource_id=f"{notification.id}"
            ))

            logger.info("NotificationViewSet: Successfully acknowledged Notification ID: %s for User ID: %s", notification_id, request.user.id)
            return Response(payload, status=status.HTTP_200_OK)
        except PermissionError as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=str(e),
                resource_id=None
            ))

            logger.error("NotificationViewSet: Permission denied acknowledging Notification ID: %s for User ID: %s - %s", notification_id, request.user.id, str(e))
            return Response(payload, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=str(e),
                resource_id=None
            ))

            logger.error("NotificationViewSet: Notification ID: %s not found for User ID: %s - %s", notification_id, request.user.id, str(e))
            return Response(payload, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error("NotificationViewSet: Failed to acknowledge Notification ID: %s for User ID: %s - %s", notification_id, request.user.id, str(e))
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to acknowledge notification: {e}",
                resource_id=None
            ))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        methods=["POST"],
        operation_id="notifications_batch_acknowledge",
        summary="Batch acknowledge notifications",
        description="Acknowledge receipt of multiple notifications at once.",
        request=BatchAcknowledgeRequestSerializer,
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer,
        }
    )
    @action(detail=False, methods=["post"], url_path="ack")
    def batch_acknowledge(self, request):
        logger.info("NotificationViewSet: Received request to batch acknowledge notifications for User ID: %s", request.user.id)
        serializer = BatchAcknowledgeRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            batch_ids = serializer.validated_data.get("batch", [])
            handler = BatchAcknowledgeNotificationCommandHandler()

            marked_read = handler.handle(BatchAcknowledgeNotificationCommand(
                user_id=request.user.id,
                notification_ids=batch_ids,
            ))
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Acknowledged {len(marked_read)} notification(s)",
                resource_id=None
            ))

            logger.info("NotificationViewSet: Successfully batch acknowledged %d notifications for User ID: %s", len(marked_read), request.user.id)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to batch acknowledge notifications: {e}",
                resource_id=None
            ))

            logger.error("NotificationViewSet: Failed to batch acknowledge notifications for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    methods=["GET"],
    operation_id="notifications_stream",
    summary="Stream notifications",
    description="Open an SSE stream to securely forward live notifications from the system.",
    responses={200: OpenApiTypes.STR}
)
@async_with_auth(authenticator=ClerkJWTAuthentication())
async def notification_stream(request):
    logger.info("notification_stream: User ID %s is opening an SSE notification stream", request.user.id)
    handler = OpenNotificationsConnectionHandler(notification_broker=application.broker)
    response = StreamingHttpResponse(
        handler.handle(OpenNotificationsConnection(
            user_id=request.user.id,
        )),
        content_type="text/event-stream",
    )

    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["X-Accel-Buffering"] = "no"

    logger.info("notification_stream: Successfully opened SSE notification stream for User ID %s", request.user.id)
    return response
