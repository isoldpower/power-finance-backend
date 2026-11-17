from rest_framework import serializers

from .envelope import collection_response, resource_response


class CategoryReferenceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    is_global = serializers.BooleanField()


class CategoryResponseSerializer(serializers.Serializer):
    id = serializers.UUIDField(help_text="Category ID")
    kind = serializers.ChoiceField(choices=["transaction", "wallet"])
    name = serializers.CharField()
    is_global = serializers.BooleanField(
        help_text="Built-in category every user sees. It cannot be renamed or deleted."
    )
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    deleted_at = serializers.DateTimeField(allow_null=True)


EnvelopedCategoryResponseSerializer = resource_response(CategoryResponseSerializer)
PaginatedCategoryResponseSerializer = collection_response(CategoryResponseSerializer)
