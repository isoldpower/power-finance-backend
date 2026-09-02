from rest_framework import serializers


class CreateWebhookRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    url = serializers.URLField()
    enabled = serializers.BooleanField(required=False, default=True)


class UpdateWebhookRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120, required=False)
    url = serializers.URLField(required=False)
    enabled = serializers.BooleanField(required=False)


class SubscribeWebhookToEventRequestSerializer(serializers.Serializer):
    event = serializers.CharField(max_length=50)
