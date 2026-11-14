from decimal import Decimal
from typing import NamedTuple

from data_read_core.shared.analytics import (
    ZERO,
    AnalyticsLedger,
    AnalyticsReportHandler,
    LedgerRow,
    LedgerSide,
    LedgerWallet,
    category_token,
)
from data_read_core.shared.money import CURRENCY_CATALOG

from .config import REPORT_NAME, FlowNodeIdentifiers, FlowNodeKind, FlowNodeLabels
from .dtos import FlowLinkDTO, FlowNodeDTO, GetAnalyticsMoneyFlowQuery, MoneyFlowDTO


class NodeDescription(NamedTuple):
    kind: FlowNodeKind
    label: str
    category: str | None
    wallet: LedgerWallet | None


class GetAnalyticsMoneyFlowQueryHandler(AnalyticsReportHandler[GetAnalyticsMoneyFlowQuery]):
    report_name = REPORT_NAME
    report_type = MoneyFlowDTO

    async def _build(self, query: GetAnalyticsMoneyFlowQuery) -> MoneyFlowDTO:
        ledger = await AnalyticsLedger.load(query.scope, self._rate_service)
        rows = await ledger.fetch_flows(query.scope.window, apply_categories=False)
        smallest_visible_amount = await _smallest_visible_amount(query.scope.currency)
        node_descriptions: dict[str, NodeDescription] = {}
        links: list[FlowLinkDTO] = []

        for wallet in ledger.selected_wallets:
            wallet_rows = [row for row in rows if row.wallet_identifier == wallet.identifier]
            for link in _wallet_links(ledger, wallet, wallet_rows, node_descriptions):
                if link.amount >= smallest_visible_amount:
                    links.append(link)

        return MoneyFlowDTO(
            nodes=_nodes_of(links, node_descriptions),
            links=sorted(links, key=lambda link: link.amount, reverse=True),
            inflow=_side_total(ledger, rows, LedgerSide.INCOME),
            outflow=_side_total(ledger, rows, LedgerSide.EXPENSE),
        )


def _wallet_links(
    ledger: AnalyticsLedger,
    wallet: LedgerWallet,
    wallet_rows: list[LedgerRow],
    node_descriptions: dict[str, NodeDescription],
) -> list[FlowLinkDTO]:
    wallet_node = f"{FlowNodeIdentifiers.WALLET_PREFIX}{wallet.identifier}"
    node_descriptions[wallet_node] = NodeDescription(
        kind=FlowNodeKind.WALLET,
        label=wallet.name,
        category=None,
        wallet=wallet,
    )
    category_amounts: dict[str, Decimal] = {}
    wallet_inflow = ZERO
    wallet_outflow = ZERO

    for row in wallet_rows:
        converted_amount = ledger.converted_magnitude(row)
        category_node = _register_category_node(row, node_descriptions)
        category_amounts[category_node] = (
            category_amounts.get(category_node, ZERO) + converted_amount
        )
        if row.side is LedgerSide.INCOME:
            wallet_inflow += converted_amount
        else:
            wallet_outflow += converted_amount

    links = [
        FlowLinkDTO(source=category_node, target=wallet_node, amount=amount)
        if node_descriptions[category_node].kind is FlowNodeKind.INCOME_CATEGORY
        else FlowLinkDTO(source=wallet_node, target=category_node, amount=amount)
        for category_node, amount in category_amounts.items()
    ]
    if wallet_inflow > wallet_outflow:
        links.append(
            FlowLinkDTO(
                source=wallet_node,
                target=FlowNodeIdentifiers.SAVINGS.value,
                amount=wallet_inflow - wallet_outflow,
            )
        )
    elif wallet_outflow > wallet_inflow:
        links.append(
            FlowLinkDTO(
                source=FlowNodeIdentifiers.RESERVES.value,
                target=wallet_node,
                amount=wallet_outflow - wallet_inflow,
            )
        )

    return links


def _register_category_node(row: LedgerRow, node_descriptions: dict[str, NodeDescription]) -> str:
    is_income = row.side is LedgerSide.INCOME
    prefix = FlowNodeIdentifiers.INCOME_PREFIX if is_income else FlowNodeIdentifiers.EXPENSE_PREFIX
    category_node = f"{prefix}{category_token(row.category)}"
    node_descriptions.setdefault(
        category_node,
        NodeDescription(
            kind=FlowNodeKind.INCOME_CATEGORY if is_income else FlowNodeKind.EXPENSE_CATEGORY,
            label=row.category if row.category is not None else FlowNodeLabels.UNCATEGORISED.value,
            category=row.category,
            wallet=None,
        ),
    )

    return category_node


def _nodes_of(
    links: list[FlowLinkDTO],
    node_descriptions: dict[str, NodeDescription],
) -> list[FlowNodeDTO]:
    incoming_amounts: dict[str, Decimal] = {}
    outgoing_amounts: dict[str, Decimal] = {}
    for link in links:
        incoming_amounts[link.target] = incoming_amounts.get(link.target, ZERO) + link.amount
        outgoing_amounts[link.source] = outgoing_amounts.get(link.source, ZERO) + link.amount

    ordered_identifiers = list(
        dict.fromkeys(identifier for link in links for identifier in (link.source, link.target))
    )

    return [
        _node_of(
            identifier,
            node_descriptions,
            max(incoming_amounts.get(identifier, ZERO), outgoing_amounts.get(identifier, ZERO)),
        )
        for identifier in ordered_identifiers
    ]


def _node_of(
    identifier: str,
    node_descriptions: dict[str, NodeDescription],
    amount: Decimal,
) -> FlowNodeDTO:
    description = node_descriptions.get(identifier) or _balancing_node_description(identifier)

    return FlowNodeDTO(
        identifier=identifier,
        kind=description.kind,
        label=description.label,
        category=description.category,
        wallet=description.wallet,
        amount=amount,
    )


def _balancing_node_description(identifier: str) -> NodeDescription:
    if identifier == FlowNodeIdentifiers.SAVINGS:
        return NodeDescription(
            kind=FlowNodeKind.SAVINGS,
            label=FlowNodeLabels.SAVINGS.value,
            category=None,
            wallet=None,
        )

    return NodeDescription(
        kind=FlowNodeKind.RESERVES,
        label=FlowNodeLabels.RESERVES.value,
        category=None,
        wallet=None,
    )


def _side_total(ledger: AnalyticsLedger, rows: list[LedgerRow], side: LedgerSide) -> Decimal:
    return sum((ledger.converted_magnitude(row) for row in rows if row.side is side), ZERO)


async def _smallest_visible_amount(currency: str) -> Decimal:
    return Decimal(1).scaleb(-await CURRENCY_CATALOG.decimals_or_default(currency))
