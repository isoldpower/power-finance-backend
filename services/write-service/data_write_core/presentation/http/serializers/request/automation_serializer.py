from rest_framework import serializers

MAX_NAME_LENGTH = 120
MAX_ICON_LENGTH = 64


class CreateAutomationRequestSerializer(serializers.Serializer):
    """Shape only. The trigger and the effects are validated by the domain,
    which owns the vocabularies and the filter grammar — a serializer would be a
    second, weaker copy of both."""

    name = serializers.CharField(max_length=MAX_NAME_LENGTH)
    icon = serializers.CharField(
        max_length=MAX_ICON_LENGTH,
        required=False,
        allow_blank=True,
        default="",
        help_text="Free-form, with a client-side registry. Never validated against a list.",
    )
    enabled = serializers.BooleanField(required=False, default=True)
    trigger = serializers.DictField()
    effects = serializers.ListField(child=serializers.DictField())


class UpdateAutomationRequestSerializer(serializers.Serializer):
    """`trigger` and `effects` are replaced WHOLE when supplied, never merged:
    deep-merging a condition tree has no sane definition."""

    name = serializers.CharField(max_length=MAX_NAME_LENGTH, required=False)
    icon = serializers.CharField(max_length=MAX_ICON_LENGTH, required=False, allow_blank=True)
    enabled = serializers.BooleanField(required=False)
    trigger = serializers.DictField(required=False)
    effects = serializers.ListField(child=serializers.DictField(), required=False)
