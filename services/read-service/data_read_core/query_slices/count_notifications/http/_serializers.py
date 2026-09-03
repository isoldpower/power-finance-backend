from rest_framework import serializers

from data_read_core.shared.rest_framework import empty_meta_field


class NotificationCountsSerializer(serializers.Serializer):
    unacknowledged = serializers.IntegerField(help_text="The badge.")
    total = serializers.IntegerField(
        help_text="Every notification the user has, acknowledged or not.",
    )


class EnvelopedNotificationCountsSerializer(serializers.Serializer):
    data = NotificationCountsSerializer()
    # The target shows `"meta": {}` here — not paginated, not cached.
    meta = empty_meta_field()
