from rest_framework import serializers


class CreateWebhookRequestSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    url = serializers.URLField()
    subscribed = serializers.ListField(
        child=serializers.CharField(max_length=60),
        allow_empty=True,
        allow_null=False,
    )