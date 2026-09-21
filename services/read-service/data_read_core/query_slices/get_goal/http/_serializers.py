from rest_framework import serializers

from data_read_core.shared.rest_framework import (
    MoneySerializer,
    resource_response,
)


class HistoryEntrySerializer(serializers.Serializer):
    id = serializers.UUIDField(
        help_text=(
            "Stable anchor for the history cursor. The target's examples omit it, "
            "but a keyset-paginated collection needs one."
        )
    )
    title = serializers.CharField()
    debit = serializers.BooleanField(help_text="True when the entry moved money IN.")
    created_at = serializers.DateTimeField()
    source_transaction = serializers.UUIDField()
    icon = serializers.CharField(
        allow_blank=True,
        help_text="Display glyph, decoration only.",
    )
    money = MoneySerializer(
        help_text="A positive magnitude; direction is `debit`.",
    )


class GoalDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    url = serializers.CharField(allow_null=True)
    currency = serializers.CharField()
    finish_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)
    target = MoneySerializer()
    progress = MoneySerializer()
    history = HistoryEntrySerializer(many=True)


EnvelopedGoalDetailSerializer = resource_response(GoalDetailSerializer)
