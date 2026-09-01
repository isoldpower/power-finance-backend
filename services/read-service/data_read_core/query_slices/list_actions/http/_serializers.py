from rest_framework import serializers

from data_read_core.shared.postgres_orm import ActionSeverity, ActionSource, ActionStatus
from data_read_core.shared.rest_framework import collection_response

RESOLUTION_INTENTS = ("primary", "secondary", "danger")


class ActionSubjectSerializer(serializers.Serializer):
    type = serializers.CharField(help_text="A resource name in this API.")
    id = serializers.CharField()


class ActionMoneySerializer(serializers.Serializer):
    amount = serializers.CharField()
    currency = serializers.CharField()


class ActionResolutionSerializer(serializers.Serializer):
    id = serializers.CharField()
    label = serializers.CharField()
    intent = serializers.ChoiceField(
        choices=RESOLUTION_INTENTS,
        help_text="A rendering hint, not behaviour. A client may style all of them identically.",
    )
    applies = serializers.BooleanField(
        help_text="Whether choosing it changes OTHER resources.",
    )


class ActionPreviewSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    source = serializers.ChoiceField(choices=[member.value for member in ActionSource])
    kind = serializers.CharField(
        help_text=(
            "An OPEN vocabulary. Use it to pick an icon and fall back to a "
            "generic one for values you do not know. Never derive labels, "
            "button counts or behaviour from it — that is what `resolutions` is."
        ),
    )
    severity = serializers.ChoiceField(choices=[member.value for member in ActionSeverity])
    status = serializers.ChoiceField(choices=[member.value for member in ActionStatus])
    title = serializers.CharField()
    body = serializers.CharField(allow_blank=True)
    subject = ActionSubjectSerializer(allow_null=True)
    money = ActionMoneySerializer(
        allow_null=True,
        help_text="In the currency the action concerns. NOT the reporting currency.",
    )
    group_key = serializers.CharField(
        allow_null=True,
        help_text="Collapses recurring conditions onto one row. Null when it does not recur.",
    )
    occurrences = serializers.IntegerField(help_text="1 for a non-recurring action, never 0.")
    last_seen_at = serializers.DateTimeField()
    expires_at = serializers.DateTimeField(allow_null=True)
    resolved_at = serializers.DateTimeField(allow_null=True)
    resolutions = ActionResolutionSerializer(
        many=True,
        help_text="Never empty while pending; always empty once answered.",
    )
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)


PaginatedActionPreviewSerializer = collection_response(ActionPreviewSerializer)
