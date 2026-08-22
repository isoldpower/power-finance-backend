from rest_framework import serializers
from write_service.common.money import MoneyAmountField

from data_write_core.domain.services import MAX_CHAIN_LENGTH
from data_write_core.domain.value_objects import TransactionOrigin, TransactionType

AMOUNT_HELP = (
    'Decimal string, e.g. "50.00". Always a positive magnitude — direction is '
    "`type`. Fewer fraction digits than the currency's scale are zero-padded; "
    "more are rejected."
)


class EvidenceSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=2048)


class TransactionFieldsMixin(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    wallet_id = serializers.UUIDField()
    currency = serializers.CharField(max_length=8)
    amount = MoneyAmountField(help_text=AMOUNT_HELP)
    type = serializers.ChoiceField(
        choices=[transaction_type.value for transaction_type in TransactionType]
    )
    origin = serializers.ChoiceField(
        choices=[o.value for o in TransactionOrigin],
        required=False,
        default=TransactionOrigin.MANUAL.value,
    )
    category = serializers.CharField(max_length=255, required=False, allow_null=True)
    evidence = EvidenceSerializer(required=False, allow_null=True)


class CreateTransactionRequestSerializer(TransactionFieldsMixin):
    pass


class ChainEntryRequestSerializer(TransactionFieldsMixin):
    temporary_id = serializers.CharField(max_length=64)
    after = serializers.CharField(max_length=64, required=False, allow_null=True)


class CreateTransactionChainRequestSerializer(serializers.Serializer):
    transactions = serializers.ListField(
        child=ChainEntryRequestSerializer(),
        min_length=1,
        max_length=MAX_CHAIN_LENGTH,
        help_text=(
            f"At most {MAX_CHAIN_LENGTH} entries. The whole chain commits in one "
            "transaction, so the bound keeps the lock window predictable."
        ),
    )


class PatchTransactionRequestSerializer(serializers.Serializer):
    """Metadata only. The money lives in an append-only ledger no request body
    in this API can reach."""

    name = serializers.CharField(max_length=255, required=False)
    category = serializers.CharField(max_length=255, required=False, allow_null=True)
    evidence = EvidenceSerializer(required=False, allow_null=True)


class AdjustTransactionRequestSerializer(serializers.Serializer):
    """Restate a transaction's amount. `amount` is the NEW TOTAL, not a delta, and
    a positive magnitude like everywhere else."""

    amount = MoneyAmountField(help_text=AMOUNT_HELP)
