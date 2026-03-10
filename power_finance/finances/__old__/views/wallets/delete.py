from rest_framework import serializers

from .common import MetaSerializer
from finances.models import Wallet


class DeleteMetaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    deleted = serializers.BooleanField(default=False)


class DeleteWalletSerializer(MetaSerializer):
    meta = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()

    class Meta:
        model = Wallet

    def get_message(self, obj):
        is_deleted = obj.deleted_at is not None
        if is_deleted:
            return f'Wallet was deleted successfully'
        else:
            return f'Wallet was not deleted'

    def get_meta(self, obj):
        is_deleted = obj.deleted_at is not None
        return DeleteMetaSerializer({ 'id': obj.id, 'deleted': is_deleted }).data
