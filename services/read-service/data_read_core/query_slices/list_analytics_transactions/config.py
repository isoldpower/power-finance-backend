from enum import StrEnum

from data_read_core.shared.analytics import IntegerBounds, ParamsList

REPORT_NAME = "list_analytics_transactions"

LIMIT_BOUNDS = IntegerBounds(parameter=ParamsList.LIMIT.value, default=20, minimum=1, maximum=50)


class TransactionOrder(StrEnum):
    AMOUNT_DESCENDING = "amount_desc"
    CREATED_DESCENDING = "created_desc"


DEFAULT_ORDER = TransactionOrder.AMOUNT_DESCENDING
