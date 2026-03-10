from rest_framework import serializers


class WalletMetaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()


class MetaSerializer(serializers.Serializer):
    meta = serializers.SerializerMethodField()

    def get_meta(self, obj):
        return WalletMetaSerializer(obj).data