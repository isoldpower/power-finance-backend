from rest_framework import serializers

from .envelope import collection_response, resource_response


class WebhookResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Webhook ID")
    title = serializers.CharField()
    url = serializers.URLField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)


class WebhookWithSecretResponseSerializer(WebhookResponseSerializer):
    secret = serializers.CharField(
        help_text="The signing secret (only shown on creation or rotation)",
    )


class WebhookSubscriptionResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Subscription ID")
    webhook_id = serializers.UUIDField()
    event_type = serializers.CharField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)


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
