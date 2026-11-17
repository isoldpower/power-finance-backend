from data_read_core.shared.analytics import (
    TransactionBriefSerializer,
    collection_meta_with,
    enveloped,
)
from data_read_core.shared.rest_framework import MoneySerializer

TransactionsMetaSerializer = collection_meta_with(
    "AnalyticsTransactionsMetaSerializer",
    total_inflow=MoneySerializer(help_text="Over every matching row."),
    total_outflow=MoneySerializer(help_text="Over every matching row."),
)

EnvelopedTransactionsSerializer = enveloped(
    "EnvelopedAnalyticsTransactionsSerializer",
    TransactionBriefSerializer(many=True),
    TransactionsMetaSerializer(),
)
