from rest_framework import serializers

from data_read_core.shared.rest_framework import resource_response


class WebhookDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    url = serializers.URLField()
    enabled = serializers.BooleanField(
        help_text="The pause switch. A disabled endpoint keeps its subscriptions and receives nothing.",
    )
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)


EnvelopedWebhookDetailSerializer = resource_response(WebhookDetailSerializer)
