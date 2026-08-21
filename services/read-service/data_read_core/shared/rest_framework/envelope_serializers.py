from rest_framework import serializers


class CollectionMetaSerializer(serializers.Serializer):
    limit = serializers.IntegerField(
        allow_null=True,
        help_text="Effective page size. Null on non-paginated endpoints.",
    )
    total = serializers.IntegerField(
        help_text="Total items matching the request, ignoring pagination.",
    )
    next_cursor = serializers.CharField(
        allow_null=True,
        help_text="Opaque token for the page after this one. Null when exhausted.",
    )
    prev_cursor = serializers.CharField(
        allow_null=True,
        help_text="Opaque token for the page before this one. Null on the first page.",
    )
    cached = serializers.BooleanField(
        required=False,
        help_text="True when the payload was served from cache rather than rebuilt.",
    )


class ResourceMetaSerializer(serializers.Serializer):
    cached = serializers.BooleanField(
        required=False,
        help_text="True when the payload was served from cache rather than rebuilt.",
    )


class ErrorDetailSerializer(serializers.Serializer):
    field = serializers.CharField(allow_null=True)
    code = serializers.CharField()
    message = serializers.CharField()


class ErrorBodySerializer(serializers.Serializer):
    code = serializers.CharField()
    message = serializers.CharField()
    details = ErrorDetailSerializer(many=True, required=False)


class ErrorMetaSerializer(serializers.Serializer):
    request_id = serializers.CharField(allow_null=True)
    timestamp = serializers.DateTimeField()


class ErrorResponseSerializer(serializers.Serializer):
    error = ErrorBodySerializer()
    meta = ErrorMetaSerializer()


def collection_response(
    item_serializer: type[serializers.Serializer],
    component_name: str | None = None,
) -> type:
    """Build the `data` + `meta` serializer for a collection."""

    return type(
        component_name or f"Paginated{item_serializer.__name__}",
        (serializers.Serializer,),
        {
            "data": item_serializer(many=True),
            "meta": CollectionMetaSerializer(),
        },
    )


def resource_response(item_serializer: type[serializers.Serializer]) -> type:
    """Build the `data` + `meta` serializer for a single resource."""

    return type(
        f"Enveloped{item_serializer.__name__}",
        (serializers.Serializer,),
        {
            "data": item_serializer(),
            "meta": ResourceMetaSerializer(),
        },
    )
