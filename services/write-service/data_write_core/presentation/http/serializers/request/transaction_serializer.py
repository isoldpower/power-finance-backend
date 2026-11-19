from rest_framework import serializers
from write_service.common.money import MoneyAmountField

from data_write_core.domain.services.config import ChainSettings
from data_write_core.domain.value_objects import (
    CLIENT_ORIGINS,
    TransactionOrigin,
    TransactionType,
)

from .config import HelpText


class EvidenceSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=2048)


class TransactionFieldsMixin(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    wallet_id = serializers.UUIDField()
    currency = serializers.CharField(max_length=8)
    amount = MoneyAmountField(help_text=HelpText.AMOUNT)
    type = serializers.ChoiceField(
        choices=[transaction_type.value for transaction_type in TransactionType]
    )
    origin = serializers.ChoiceField(
        choices=[origin.value for origin in CLIENT_ORIGINS],
        required=False,
        default=TransactionOrigin.MANUAL.value,
    )
    category_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text=HelpText.TRANSACTION_CATEGORY,
    )
    evidence = EvidenceSerializer(required=False, allow_null=True)


class CreateTransactionRequestSerializer(TransactionFieldsMixin):
    pass


NEW_MEMBER_REQUIRED_FIELDS = ("name", "wallet_id", "currency", "amount", "type")
NEW_MEMBER_OPTIONAL_FIELDS = ("origin", "category_id", "evidence")
BOUND_MEMBER_CONFLICT_MESSAGE = "Not allowed together with transaction_id."
REQUIRED_FIELD_MESSAGE = "This field is required."
REQUIRED_FIELD_CODE = "required"


class ChainMemberFieldsMixin(serializers.Serializer):
    transaction_id = serializers.UUIDField(
        required=False,
        help_text=(
            "Bind this existing transaction instead of creating a new one. When set, "
            "the new-transaction fields must be left out."
        ),
    )
    name = serializers.CharField(max_length=255, required=False)
    wallet_id = serializers.UUIDField(required=False)
    currency = serializers.CharField(max_length=8, required=False)
    amount = MoneyAmountField(required=False, help_text=HelpText.AMOUNT)
    type = serializers.ChoiceField(
        choices=[transaction_type.value for transaction_type in TransactionType],
        required=False,
    )
    origin = serializers.ChoiceField(
        choices=[origin.value for origin in CLIENT_ORIGINS],
        required=False,
    )
    category_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text=HelpText.TRANSACTION_CATEGORY,
    )
    evidence = EvidenceSerializer(required=False, allow_null=True)

    def validate(self, attrs: dict) -> dict:
        if "transaction_id" in attrs:
            conflicting_fields = [
                field
                for field in (*NEW_MEMBER_REQUIRED_FIELDS, *NEW_MEMBER_OPTIONAL_FIELDS)
                if field in attrs
            ]
            if conflicting_fields:
                raise serializers.ValidationError(
                    {field: BOUND_MEMBER_CONFLICT_MESSAGE for field in conflicting_fields}
                )
            return attrs

        missing_fields = [field for field in NEW_MEMBER_REQUIRED_FIELDS if field not in attrs]
        if missing_fields:
            raise serializers.ValidationError(
                {
                    field: serializers.ErrorDetail(REQUIRED_FIELD_MESSAGE, code=REQUIRED_FIELD_CODE)
                    for field in missing_fields
                }
            )

        return attrs


class AttachChainTransactionRequestSerializer(ChainMemberFieldsMixin):
    pass


class ChainEntryRequestSerializer(ChainMemberFieldsMixin):
    temporary_id = serializers.CharField(max_length=64)
    after = serializers.CharField(max_length=64, required=False, allow_null=True)


class CreateTransactionChainRequestSerializer(serializers.Serializer):
    transactions = serializers.ListField(
        child=ChainEntryRequestSerializer(),
        min_length=1,
        max_length=ChainSettings.MAX_CHAIN_LENGTH,
        help_text=(
            f"At most {ChainSettings.MAX_CHAIN_LENGTH} entries. The whole chain commits in one "
            "transaction, so the bound keeps the lock window predictable."
        ),
    )


class PatchTransactionRequestSerializer(serializers.Serializer):
    """Metadata only. The money lives in an append-only ledger no request body
    in this API can reach."""

    name = serializers.CharField(max_length=255, required=False)
    category_id = serializers.UUIDField(
        required=False,
        allow_null=True,
        help_text=HelpText.TRANSACTION_CATEGORY,
    )
    evidence = EvidenceSerializer(required=False, allow_null=True)


class AdjustTransactionRequestSerializer(serializers.Serializer):
    """Restate a transaction's amount. `amount` is the NEW TOTAL, not a delta, and
    a positive magnitude like everywhere else."""

    amount = MoneyAmountField(help_text=HelpText.AMOUNT)
