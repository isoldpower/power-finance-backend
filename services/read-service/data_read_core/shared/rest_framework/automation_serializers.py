from rest_framework import serializers

TRIGGER_TYPES = ("event", "schedule")
TRIGGER_EVENTS = ("transaction.created", "transaction.updated")
TRIGGER_SCHEDULES = ("daily", "weekly", "monthly")
EFFECT_TYPES = ("set_category", "notify", "raise_action", "transfer")


class AutomationTriggerSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=TRIGGER_TYPES)
    event = serializers.ChoiceField(
        choices=TRIGGER_EVENTS,
        allow_null=True,
        help_text="Null unless `type` is `event`. Always present.",
    )
    schedule = serializers.ChoiceField(
        choices=TRIGGER_SCHEDULES,
        allow_null=True,
        help_text="Null unless `type` is `schedule`. Always present.",
    )
    filter_body = serializers.DictField(
        allow_null=True,
        help_text=(
            "The same filter tree the `/search` endpoints take. Null means the "
            "rule is unconditional."
        ),
    )


class AutomationEffectSerializer(serializers.Serializer):
    type = serializers.ChoiceField(choices=EFFECT_TYPES)
    params = serializers.DictField()


def automation_fields() -> dict:
    """The whole rule. The list returns the COMPLETE resource rather than a
    preview — a rule is small and the browser renders its condition inline — so
    both slices are built from one field set."""

    return {
        "id": serializers.UUIDField(),
        "name": serializers.CharField(),
        "icon": serializers.CharField(allow_blank=True),
        "enabled": serializers.BooleanField(),
        "trigger": AutomationTriggerSerializer(),
        "effects": AutomationEffectSerializer(many=True),
        "last_run_at": serializers.DateTimeField(allow_null=True),
        "runs": serializers.IntegerField(
            help_text=(
                "MATCHES that applied effects, not evaluations. A rule checked a "
                "thousand times that never matched reports 0."
            ),
        ),
        "created_at": serializers.DateTimeField(),
        "updated_at": serializers.DateTimeField(allow_null=True),
        "deleted_at": serializers.DateTimeField(allow_null=True),
    }
