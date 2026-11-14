from data_read_core.shared.analytics import (
    AnalyticsScope,
    present_scope_meta,
    present_wallet_reference,
)
from data_read_core.shared.money import money_at_scale

from ..dtos import FlowLinkDTO, FlowNodeDTO, MoneyFlowDTO


async def present_money_flow(money_flow: MoneyFlowDTO, currency: str) -> dict:
    return {
        "nodes": [await _present_node(node, currency) for node in money_flow.nodes],
        "links": [await _present_link(link, currency) for link in money_flow.links],
        "totals": {
            "inflow": await money_at_scale(money_flow.inflow, currency),
            "outflow": await money_at_scale(money_flow.outflow, currency),
        },
    }


def present_meta(scope: AnalyticsScope, cached: bool) -> dict:
    return present_scope_meta(scope, cached)


async def _present_node(node: FlowNodeDTO, currency: str) -> dict:
    return {
        "id": node.identifier,
        "kind": node.kind.value,
        "label": node.label,
        "category": node.category,
        "wallet": present_wallet_reference(node.wallet) if node.wallet else None,
        "amount": await money_at_scale(node.amount, currency),
    }


async def _present_link(link: FlowLinkDTO, currency: str) -> dict:
    return {
        "source": link.source,
        "target": link.target,
        "amount": await money_at_scale(link.amount, currency),
    }
