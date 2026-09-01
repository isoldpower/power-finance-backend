from rest_framework import serializers


class NotificationCountsSerializer(serializers.Serializer):
    unacknowledged = serializers.IntegerField(help_text="The badge.")
    total = serializers.IntegerField(
        help_text="Every notification the user has, acknowledged or not.",
    )


class EmptyMetaSerializer(serializers.Serializer):
    """The target shows `"meta": {}` here — not paginated, not cached."""

    pass


class EnvelopedNotificationCountsSerializer(serializers.Serializer):
    data = NotificationCountsSerializer()
    meta = EmptyMetaSerializer()
