from rest_framework import serializers


class MessageMetaSerializer(serializers.Serializer):
    id = serializers.CharField(allow_null=True)


class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField()
    meta = MessageMetaSerializer()
