from rest_framework import serializers


class CreateWebhookRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    url = serializers.URLField()

class UpdateWebhookRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120, required=False)
    url = serializers.URLField(required=False)


class RotateWebhookSecretRequestSerializer(serializers.Serializer):
    pass


class SubscribeWebhookToEventRequestSerializer(serializers.Serializer):
    event_type = serializers.CharField(max_length=50)