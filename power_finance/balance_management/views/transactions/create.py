from rest_framework import serializers
from django.db import transaction as db_transaction

from .common import TransactionWalletPreviewSerializer, TransactionSideDetailedSerializer
from ...models import Transaction, TransactionType
from ...services.adjust_wallet_balances import adjust_wallet_balances


class CreateTransactionSerializer(serializers.ModelSerializer):
    from_side = TransactionWalletPreviewSerializer(required=False, allow_null=True)
    to_side = TransactionWalletPreviewSerializer(required=False, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True)
    type = serializers.ChoiceField(choices=TransactionType.choices)

    class Meta:
        model = Transaction
        fields = ['from_side', 'to_side', 'description', 'type']

    def to_internal_value(self, data):
        data = data.copy()
        if 'from' in data:
            data['from_side'] = data.pop('from')
        if 'to' in data:
            data['to_side'] = data.pop('to')
        return super().to_internal_value(data)

    def to_representation(self, instance):
        from_data = None
        if instance.from_wallet:
            from_data = TransactionSideDetailedSerializer({
                'wallet': instance.from_wallet,
                'amount': instance.from_amount,
            }).data

        to_data = None
        if instance.to_wallet:
            to_data = TransactionSideDetailedSerializer({
                'wallet': instance.to_wallet,
                'amount': instance.to_amount,
            }).data

        return {
            "data": {
                "id": str(instance.id),
                "created_at": instance.created_at,
                "description": instance.description,
                "from": from_data,
                "to": to_data,
            },
            "type": instance.type,
            "id": str(instance.id),
            "meta": {
                "id": str(instance.id),
                "created_at": instance.created_at,
            }
        }

    def create(self, validated_data):
        from_data = validated_data.pop('from_side', None)
        to_data = validated_data.pop('to_side', None)

        with db_transaction.atomic():
            if from_data:
                validated_data['from_wallet_id'] = from_data.get('wallet')
                validated_data['from_amount'] = from_data.get('amount')

            if to_data:
                validated_data['to_wallet_id'] = to_data.get('wallet')
                validated_data['to_amount'] = to_data.get('amount')

            new_transaction = Transaction.objects.create(**validated_data)
            adjust_wallet_balances(new_transaction)

        return new_transaction

