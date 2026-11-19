from rest_framework import serializers


class CategoryReferenceSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    is_global = serializers.BooleanField()
