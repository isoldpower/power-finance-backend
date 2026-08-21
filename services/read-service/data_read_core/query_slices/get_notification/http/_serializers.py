from rest_framework import serializers

from data_read_core.shared.rest_framework import resource_response


class NotificationResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    short = serializers.CharField()
    message = serializers.CharField()
    payload = serializers.JSONField(allow_null=True)
    is_read = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)


EnvelopedNotificationResponseSerializer = resource_response(NotificationResponseSerializer)
