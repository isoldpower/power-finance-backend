from rest_framework import serializers


class NotificationSubjectSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.CharField(
        help_text="Open vocabulary — `wallet`, `transaction`, and whatever comes next.",
    )
