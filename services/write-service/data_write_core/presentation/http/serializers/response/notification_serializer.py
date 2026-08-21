from rest_framework import serializers

from .envelope import collection_response, resource_response


class NotificationResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Notification ID")
    short = serializers.CharField()
    message = serializers.CharField()
    payload = serializers.JSONField(allow_null=True)
    is_read = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)


class AcknowledgedNotificationsSerializer(serializers.Serializer):
    acknowledged_ids = serializers.ListField(child=serializers.UUIDField())


EnvelopedNotificationResponseSerializer = resource_response(NotificationResponseSerializer)
PaginatedNotificationResponseSerializer = collection_response(NotificationResponseSerializer)
AcknowledgedNotificationsResponseSerializer = resource_response(AcknowledgedNotificationsSerializer)
