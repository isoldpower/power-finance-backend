from rest_framework import serializers


class PaginationMetaSerializer(serializers.Serializer):
    limit = serializers.IntegerField(help_text="Number of items per page")
    offset = serializers.IntegerField(help_text="Number of items skipped")
    total = serializers.IntegerField(help_text="Total number of items available")


class MessageMetaSerializer(serializers.Serializer):
    id = serializers.CharField(required=False, allow_null=True, help_text="Resource ID related to the message")

class MessageResponseSerializer(serializers.Serializer):
    message = serializers.CharField(help_text="Human-readable status or error message")
    meta = MessageMetaSerializer(help_text="Additional metadata")
