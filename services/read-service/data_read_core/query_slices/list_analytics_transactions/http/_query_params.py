from rest_framework.request import Request

from data_read_core.shared.analytics import Messages, ParamsList, read_choice
from data_read_core.shared.http_contract import DetailCode

from ..config import DEFAULT_ORDER, TransactionOrder


def read_order(request: Request) -> TransactionOrder:
    requested_order = read_choice(
        request,
        ParamsList.ORDER,
        TransactionOrder,
        DetailCode.ORDER_INVALID,
        Messages.UNKNOWN_ORDER,
    )

    return requested_order or DEFAULT_ORDER


def read_counterparty_name(request: Request) -> str | None:
    return request.query_params.get(ParamsList.NAME)
