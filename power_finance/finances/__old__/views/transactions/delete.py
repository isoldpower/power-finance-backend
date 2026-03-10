from rest_framework import serializers

from finances.models import Transaction


class DeleteMetaSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    deleted = serializers.BooleanField(default=False)


class DeleteTransactionSerializer(serializers.Serializer):
    meta = DeleteMetaSerializer()
    message = serializers.CharField()

    class Meta:
        model = Transaction

    def get_message(self, obj):
        is_deleted = obj.deleted_at is not None
        if is_deleted:
            return f'Transaction was deleted successfully'
        else:
            return f'Transaction was not deleted'

    def get_meta(self, obj):
        is_deleted = obj.deleted_at is not None
        return DeleteMetaSerializer({ 'id': obj.id, 'deleted': is_deleted }).data
