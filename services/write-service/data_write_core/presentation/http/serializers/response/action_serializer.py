from rest_framework import serializers

from data_write_core.domain.entities import ActionSeverity, ActionSource, ActionStatus
from data_write_core.domain.value_objects import ResolutionIntent

from .envelope import collection_response, resource_response


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
        choices=[intent.value for intent in ResolutionIntent],
        help_text="A rendering hint, not behaviour. A client may style all of them identically.",
    )
    applies = serializers.BooleanField(
        help_text="Whether choosing it changes OTHER resources.",
    )


class ActionResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    source = serializers.ChoiceField(choices=[source.value for source in ActionSource])
    kind = serializers.CharField(
        help_text=(
            "An OPEN vocabulary. Use it to pick an icon and fall back to a "
            "generic one for values you do not know. Never derive labels, "
            "button counts or behaviour from it — that is what `resolutions` is."
        ),
    )
    severity = serializers.ChoiceField(choices=[severity.value for severity in ActionSeverity])
    status = serializers.ChoiceField(choices=[status.value for status in ActionStatus])
    title = serializers.CharField()
    body = serializers.CharField(allow_blank=True)
    subject = ActionSubjectSerializer(allow_null=True)
    money = ActionMoneySerializer(allow_null=True)
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


EnvelopedActionResponseSerializer = resource_response(ActionResponseSerializer)
PaginatedActionResponseSerializer = collection_response(ActionResponseSerializer)
