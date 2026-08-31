from rest_framework import serializers

from data_read_core.shared.rest_framework import MoneySerializer, collection_response


class AccountPostingSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    account_id = serializers.UUIDField()
    transaction_id = serializers.UUIDField()
    title = serializers.CharField(allow_blank=True)
    icon = serializers.CharField(allow_blank=True)
    debit = serializers.BooleanField(help_text="True debits the account, false credits it")
    position = serializers.IntegerField()
    money = MoneySerializer()
    created_at = serializers.DateTimeField()


PaginatedAccountPostingSerializer = collection_response(AccountPostingSerializer)
