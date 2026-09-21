from rest_framework import serializers

from .envelope import collection_response, resource_response


class WebhookResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Webhook ID")
    title = serializers.CharField()
    url = serializers.URLField()
    enabled = serializers.BooleanField(
        help_text="The pause switch. A disabled endpoint keeps its subscriptions and receives nothing.",
    )
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)


class WebhookWithSecretResponseSerializer(WebhookResponseSerializer):
    secret = serializers.CharField(
        help_text="The signing secret (only shown on creation or rotation)",
    )


class WebhookSubscriptionResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Subscription ID")
    webhook_id = serializers.UUIDField()
    event = serializers.CharField(help_text="An `event` from GET /webhooks/event-types.")
    created_at = serializers.DateTimeField()


EnvelopedWebhookResponseSerializer = resource_response(WebhookResponseSerializer)
PaginatedWebhookResponseSerializer = collection_response(WebhookResponseSerializer)
EnvelopedWebhookWithSecretResponseSerializer = resource_response(
    WebhookWithSecretResponseSerializer
)
EnvelopedWebhookSubscriptionResponseSerializer = resource_response(
    WebhookSubscriptionResponseSerializer
)
PaginatedWebhookSubscriptionResponseSerializer = collection_response(
    WebhookSubscriptionResponseSerializer
)
