from rest_framework import serializers

from data_read_core.shared.postgres_orm import Severity
from data_read_core.shared.rest_framework import (
    NotificationSubjectSerializer,
    resource_response,
)


class NotificationDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    severity = serializers.ChoiceField(
        choices=list(Severity),
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


EnvelopedNotificationDetailSerializer = resource_response(NotificationDetailSerializer)
