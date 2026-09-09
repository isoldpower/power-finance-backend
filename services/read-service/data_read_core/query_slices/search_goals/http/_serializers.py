from rest_framework import serializers

from data_read_core.shared.rest_framework import MoneySerializer, collection_response


class FilterGoalsRequestSerializer(serializers.Serializer):
    filter_body = serializers.JSONField(allow_null=False, required=True)


class GoalSearchResultSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    url = serializers.CharField(
        allow_null=True,
        help_text="Always null for now. Reserved for attaching an e-commerce link.",
    )
    currency = serializers.CharField(
        help_text="Fixed at creation; target and progress use it.",
    )
    finish_at = serializers.DateTimeField(allow_null=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)
    target = MoneySerializer()
    progress = MoneySerializer(
        help_text="Derived from the goal's transactions, never written.",
    )


PaginatedGoalSearchResultSerializer = collection_response(GoalSearchResultSerializer)
