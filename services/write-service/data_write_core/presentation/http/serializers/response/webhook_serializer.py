from rest_framework import serializers


class WebhookResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Webhook ID")
    title = serializers.CharField()
    url = serializers.URLField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


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
