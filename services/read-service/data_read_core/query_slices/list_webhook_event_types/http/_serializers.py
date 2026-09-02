from rest_framework import serializers

from data_read_core.shared.rest_framework import collection_response


class WebhookEventTypeSerializer(serializers.Serializer):
    event = serializers.CharField(
        help_text="The value a subscription names and the `X-Webhook-Event` header carries.",
    )
    subject = serializers.CharField(
        help_text="The resource the delivery payload's `data` carries.",
    )
    description = serializers.CharField(
        help_text="Human-readable label for the subscription UI. Not a contract — never parse it.",
    )


WebhookEventTypeCollectionSerializer = collection_response(
    WebhookEventTypeSerializer,
    component_name="WebhookEventTypeCollectionSerializer",
)
