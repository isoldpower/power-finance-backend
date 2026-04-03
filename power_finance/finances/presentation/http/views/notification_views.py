import uuid
from django.http import HttpResponseForbidden, StreamingHttpResponse
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

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
        try:
            handler = ListNotificationsQueryHandler()
            notifications = handler.handle(ListNotificationsQuery(
                user_id=request.user.id
            ))

            paginator = self.pagination_class()
            queryset_page = paginator.paginate_queryset(notifications, request)
            payload = NotificationHttpPresenter.present_many(queryset_page)

            return paginator.get_paginated_response(payload)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to list notifications: {e}",
                resource_id=None
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)


    @extend_schema(
        methods=["POST"],
        operation_id="notifications_acknowledge",
        summary="Acknowledge notification",
        description="Acknowledge receipt of a notification, marking it as delivered. This stops the SSE stream from sending it again.",
        parameters=[
            OpenApiParameter('notification_id', type=OpenApiTypes.UUID, location=OpenApiParameter.PATH, description="Notification ID")
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

            return Response(payload, status=status.HTTP_200_OK)
        except PermissionError as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=str(e),
                resource_id=None
            ))
            return Response(payload, status=status.HTTP_403_FORBIDDEN)
        except ValueError as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=str(e),
                resource_id=None
            ))
            return Response(payload, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to acknowledge notification: {e}",
                resource_id=None
            ))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        methods=["GET"],
        operation_id="notifications_stream",
        summary="Stream notifications",
        description="Open an SSE stream to securely forward live notifications from the system.",
        responses={200: OpenApiTypes.STR}
    )
    @action(detail=False, methods=["get"], url_path="stream")
    def stream(self, request):
        if not application or not application.initialized:
            return HttpResponseForbidden("Application is not yet initialized")

        handler = OpenNotificationsConnectionHandler(
            notification_broker=application.broker
        )
        response = StreamingHttpResponse(
            handler.handle(OpenNotificationsConnection(
                user_id=request.user.id,
            )),
            content_type="text/event-stream",
        )
        response["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response["X-Accel-Buffering"] = "no"

        return response

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

            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to batch acknowledge notifications: {e}",
                resource_id=None
            ))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
