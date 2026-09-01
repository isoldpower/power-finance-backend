from rest_framework import serializers


class ResolveActionRequestSerializer(serializers.Serializer):
    resolution_id = serializers.CharField(
        help_text=(
            "One of the ids offered on THIS action. Anything else fails with "
            "422 `unknown_resolution` — including an id that is valid on a "
            "different action."
        ),
    )
