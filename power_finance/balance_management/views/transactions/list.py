from rest_framework import serializers

from ...models import Transaction
from .common import TransactionSideDetailedSerializer


class ListTransactionsSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    type = serializers.CharField(read_only=True)
    data = serializers.SerializerMethodField()
    meta = serializers.SerializerMethodField()

    class Meta:
        model = Transaction
        fields = ['id', 'type', 'data', 'meta']
        read_only_fields = fields

    def get_meta(self, obj):
        return {
            'id': obj.id,
            'created_at': obj.created_at,
        }

    def get_data(self, obj):
        return {
            'id': obj.id,
            'created_at': obj.created_at,
            'from': TransactionSideDetailedSerializer(obj.from_data).data if obj.from_data else None,
            'to': TransactionSideDetailedSerializer(obj.to_data).data if obj.to_data else None,
            'description': obj.description
        }
