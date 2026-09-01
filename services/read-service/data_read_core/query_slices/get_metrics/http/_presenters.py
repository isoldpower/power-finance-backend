from decimal import ROUND_HALF_UP, Decimal

from data_read_core.shared.metrics import MetricsWindow
from data_read_core.shared.money import money_at_scale
from data_read_core.shared.timestamps import to_iso

from ..dtos import (
    ALL_SECTIONS,
    BalanceSheetDTO,
    MetricsDTO,
    Section,
)

PERCENTAGE_EXPONENT = Decimal("0.01")
IDENTITY_DRIFT_COMMENT = "Assets do not equal liabilities plus equity; the chart is off by {drift}."
UNBALANCED_DISPATCH_COMMENT = (
    "{count} transaction(s) were posted with legs that did not agree, most often "
    "because the two sides landed in different currencies."
)
COMMENT_SEPARATOR = " "


async def present_metrics(metrics: MetricsDTO) -> dict:
    return {
        Section.BALANCE.key: await _present_balance(metrics),
        Section.NET_WORTH.key: await _present_net_worth(metrics),
        Section.CASH_FLOW.key: await _present_cash_flow(metrics),
    }


def present_meta(
    window: MetricsWindow,
    points: int,
    sections: frozenset[Section],
    cached: bool,
) -> dict:
    return {
        "since": to_iso(window.since),
        "points": points,
        "sections": [section.value for section in ALL_SECTIONS if section in sections],
        "cached": cached,
    }


async def _present_balance(metrics: MetricsDTO) -> dict | None:
    metrics_balance = metrics.balance
    if metrics_balance is None:
        return None

    return {
        "assets": await money_at_scale(
            metrics_balance.assets,
            metrics.currency,
        ),
        "liabilities": await money_at_scale(
            metrics_balance.liabilities,
            metrics.currency,
        ),
        "equity": await money_at_scale(
            metrics_balance.equity,
            metrics.currency,
        ),
        "balanced": metrics_balance.balanced,
        "comments": _comments_for(metrics_balance),
    }


async def _present_net_worth(metrics: MetricsDTO) -> dict | None:
    net_worth = metrics.net_worth
    if net_worth is None:
        return None

    return {
        "money": await money_at_scale(net_worth.total_amount, metrics.currency),
        "net_diff": {
            "percentage": _as_percentage(net_worth.percentage),
            "direction": str(net_worth.direction),
        },
        "series": [
            {
                "timestamp": to_iso(point.timestamp),
                "money": await money_at_scale(
                    point.amount,
                    metrics.currency,
                ),
            }
            for point in net_worth.points_series
        ],
    }


async def _present_cash_flow(metrics: MetricsDTO) -> dict | None:
    cash_flow = metrics.cash_flow
    if cash_flow is None:
        return None

    return {
        "inflow": await money_at_scale(
            cash_flow.inflow,
            metrics.currency,
        ),
        "outflow": await money_at_scale(
            cash_flow.outflow,
            metrics.currency,
        ),
        "total_net": await money_at_scale(
            cash_flow.total_net,
            metrics.currency,
        ),
        "savings_rate": _as_percentage(cash_flow.savings_rate),
    }


def _comments_for(balance: BalanceSheetDTO) -> str | None:
    reasons_list = []
    if not balance.identity_holds:
        reasons_list.append(IDENTITY_DRIFT_COMMENT.format(drift=balance.drift))
    if balance.unbalanced_dispatches:
        reasons_list.append(UNBALANCED_DISPATCH_COMMENT.format(count=balance.unbalanced_dispatches))

    return COMMENT_SEPARATOR.join(reasons_list) or None


def _as_percentage(value: Decimal | None) -> float | None:
    if value is None:
        return None

    return float(
        value.quantize(
            PERCENTAGE_EXPONENT,
            rounding=ROUND_HALF_UP,
        )
    )
