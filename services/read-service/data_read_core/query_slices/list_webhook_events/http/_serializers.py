from rest_framework import serializers


class WebhookSubscriptionResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    webhook_id = serializers.UUIDField()
    event_type = serializers.CharField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()


class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    resource_id = serializers.CharField(allow_null=True)
