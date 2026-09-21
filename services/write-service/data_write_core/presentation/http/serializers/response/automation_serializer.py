from rest_framework import serializers

from data_write_core.domain.automations import (
    EFFECT_TYPE_CHOICES,
    TRIGGER_EVENT_CHOICES,
    TRIGGER_SCHEDULE_CHOICES,
    TRIGGER_TYPE_CHOICES,
)

from .envelope import collection_response, resource_response


class AutomationTriggerSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=TRIGGER_TYPE_CHOICES)
    event = serializers.ChoiceField(
        choices=TRIGGER_EVENT_CHOICES,
        allow_null=True,
        help_text="Null unless `type` is `event`. Always present.",
    )
    schedule = serializers.ChoiceField(
        choices=TRIGGER_SCHEDULE_CHOICES,
        allow_null=True,
        help_text="Null unless `type` is `schedule`. Always present.",
    )
    filter_body = serializers.DictField(
        allow_null=True,
        help_text=(
            "The same filter tree the `/search` endpoints take, validated "
            "against the policy of the trigger's SUBJECT resource. Null means "
            "the rule is unconditional."
        ),
    )


class AutomationEffectSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=EFFECT_TYPE_CHOICES)
    params = serializers.DictField(
        help_text="Exactly the params that effect type documents — no other keys.",
    )


class AutomationResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    icon = serializers.CharField(allow_blank=True)
    enabled = serializers.BooleanField()
    trigger = AutomationTriggerSerializer()
    effects = AutomationEffectSerializer(many=True)
    last_run_at = serializers.DateTimeField(allow_null=True)
    runs = serializers.IntegerField(
        help_text=(
            "MATCHES that applied effects, not evaluations. A rule checked a "
            "thousand times that never matched reports 0."
        ),
    )
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)


EnvelopedAutomationResponseSerializer = resource_response(AutomationResponseSerializer)
PaginatedAutomationResponseSerializer = collection_response(AutomationResponseSerializer)
