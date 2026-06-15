from rest_framework import serializers


class NotificationResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    short = serializers.CharField()
    message = serializers.CharField()
    payload = serializers.DictField(allow_null=True)
    is_read = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    resource_id = serializers.CharField(allow_null=True)
