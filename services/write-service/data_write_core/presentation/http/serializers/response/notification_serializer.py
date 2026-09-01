from rest_framework import serializers

from data_write_core.infrastructure.messaging import SEVERITIES

from .envelope import collection_response, resource_response


class NotificationSubjectSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.CharField(
        help_text="Open vocabulary — `wallet`, `transaction`, and whatever comes next.",
    )


class NotificationResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Notification ID")
    severity = serializers.ChoiceField(
        choices=SEVERITIES,
        help_text="Shares its vocabulary with action severity on purpose.",
    )
    title = serializers.CharField()
    body = serializers.CharField(
        help_text=(
            "Already-rendered prose. Money inside it is part of the sentence the "
            "backend generated; there is no money object to substitute."
        ),
    )
    subject = NotificationSubjectSerializer(
        allow_null=True,
        help_text="What the client deep-links to when the notification is tapped.",
    )
    acknowledged_at = serializers.DateTimeField(
        allow_null=True,
        help_text="Null means unread. A timestamp, not a boolean.",
    )
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)


EnvelopedNotificationResponseSerializer = resource_response(NotificationResponseSerializer)
PaginatedNotificationResponseSerializer = collection_response(NotificationResponseSerializer)
