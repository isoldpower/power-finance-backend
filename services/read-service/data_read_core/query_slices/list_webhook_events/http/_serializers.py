from rest_framework import serializers

from data_read_core.shared.rest_framework import collection_response


class WebhookSubscriptionResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    webhook_id = serializers.UUIDField()
    event = serializers.CharField(help_text="An `event` from GET /webhooks/event-types.")
    created_at = serializers.DateTimeField()


WebhookSubscriptionCollectionSerializer = collection_response(WebhookSubscriptionResponseSerializer)
