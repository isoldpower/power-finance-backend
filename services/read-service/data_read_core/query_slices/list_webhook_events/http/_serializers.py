from rest_framework import serializers

from data_read_core.shared.rest_framework import collection_response


class WebhookSubscriptionResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    webhook_id = serializers.UUIDField()
    event_type = serializers.CharField()
    is_active = serializers.BooleanField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)


WebhookSubscriptionCollectionSerializer = collection_response(WebhookSubscriptionResponseSerializer)
