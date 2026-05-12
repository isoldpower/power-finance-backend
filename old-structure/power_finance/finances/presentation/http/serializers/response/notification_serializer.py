from rest_framework import serializers


class NotificationResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    short = serializers.CharField()
    message = serializers.CharField()
    is_read = serializers.BooleanField(required=False, default=False)
    payload = serializers.JSONField()
    created_at = serializers.DateTimeField()
    received_at = serializers.DateTimeField(required=False, allow_null=True)
