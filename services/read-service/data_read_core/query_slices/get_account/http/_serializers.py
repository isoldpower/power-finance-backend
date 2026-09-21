from rest_framework import serializers

from data_read_core.shared.rest_framework import (
    MoneySerializer,
    resource_response,
)


class AccountHistoryEntrySerializer(serializers.Serializer):
    id = serializers.UUIDField(
        help_text=(
            "Stable anchor for the history cursor. The target's examples omit it, "
            "but a keyset-paginated collection needs one."
        )
    )
    title = serializers.CharField(allow_blank=True)
    debit = serializers.BooleanField(help_text="True debits the account, false credits it.")
    created_at = serializers.DateTimeField()
    source_transaction = serializers.UUIDField()
    icon = serializers.CharField(
        allow_blank=True,
        help_text="Display glyph, decoration only.",
    )
    money = MoneySerializer(
        help_text=(
            "The leg at the TRANSACTION's currency, which is not necessarily "
            "the book currency the account's balance is summed in."
        ),
    )


class AccountDetailSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    group = serializers.CharField(allow_blank=True)
    name = serializers.CharField()
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField(allow_null=True)
    money = MoneySerializer()
    history = AccountHistoryEntrySerializer(many=True)


EnvelopedAccountDetailSerializer = resource_response(AccountDetailSerializer)
