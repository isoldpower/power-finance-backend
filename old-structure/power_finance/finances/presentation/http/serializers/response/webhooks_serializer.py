from rest_framework import serializers


class WebhookMetaResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Webhook ID")
    created_at = serializers.DateTimeField(help_text="Creation timestamp")
    updated_at = serializers.DateTimeField(help_text="Last update timestamp")


class WebhookResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Webhook UUID")
    url = serializers.URLField(help_text="Target URL")
    title = serializers.CharField(help_text="Webhook title")
    meta = WebhookMetaResponseSerializer(help_text="Webhook metadata")


class WebhookWithSecretResponseSerializer(WebhookResponseSerializer):
    secret = serializers.CharField(help_text="The signing secret (only shown on creation or rotation)")


class WebhookSimpleResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Webhook UUID")
    url = serializers.URLField(help_text="Target URL")
    title = serializers.CharField(help_text="Webhook title")


class WebhookSubscriptionResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Subscription ID")
    event_type = serializers.CharField(help_text="Event type subscribed to")
    is_active = serializers.BooleanField(help_text="Activity status")