from rest_framework import serializers

from data_read_core.shared.postgres_orm import CategoryKinds
from data_read_core.shared.rest_framework import collection_response


class CategorySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.ChoiceField(choices=[kind.value for kind in CategoryKinds])
    name = serializers.CharField()
    is_global = serializers.BooleanField(
        help_text="Built-in category every user sees. It cannot be renamed or deleted.",
    )
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)


PaginatedCategorySerializer = collection_response(CategorySerializer)
