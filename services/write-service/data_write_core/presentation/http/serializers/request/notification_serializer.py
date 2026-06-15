from rest_framework import serializers


class BatchAcknowledgeRequestSerializer(serializers.Serializer):
    batch = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        help_text="Notification IDs to mark as read",
    )
