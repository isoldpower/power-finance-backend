from rest_framework import serializers

from data_read_core.shared.rest_framework import resource_response


class WebhookDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    url = serializers.URLField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)


EnvelopedWebhookDetailSerializer = resource_response(WebhookDetailSerializer)
