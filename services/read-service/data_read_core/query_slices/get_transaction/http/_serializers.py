from rest_framework import serializers

from data_read_core.shared.rest_framework import (
    resource_response,
    transaction_preview_fields,
)


class TransactionEvidenceSerializer(serializers.Serializer):
    url = serializers.URLField()


class TransactionAnalysisSerializer(serializers.Serializer):
    balanced = serializers.BooleanField()
    comment = serializers.CharField(allow_null=True)


class TransactionPostingSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    account_id = serializers.UUIDField()
    title = serializers.CharField()
    icon = serializers.CharField(allow_blank=True)
    debit = serializers.BooleanField()
    position = serializers.IntegerField()
    money = serializers.DictField()


class TransactionDetailSerializer(serializers.Serializer):
    evidence = TransactionEvidenceSerializer(allow_null=True)
    postings = TransactionPostingSerializer(
        many=True,
        help_text="Backend-derived double-entry legs",
    )
    analysis = TransactionAnalysisSerializer(allow_null=True)


TransactionDetailSerializer._declared_fields.update(transaction_preview_fields())

EnvelopedTransactionDetailSerializer = resource_response(TransactionDetailSerializer)
