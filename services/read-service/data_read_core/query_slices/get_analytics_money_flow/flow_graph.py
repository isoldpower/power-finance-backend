from decimal import Decimal
from typing import NamedTuple

from data_read_core.shared.analytics import (
    ZERO,
    AnalyticsCategory,
    AnalyticsLedger,
    LedgerRow,
    LedgerSide,
    LedgerWallet,
    category_token,
)

from .config import FlowNodeIdentifiers, FlowNodeKind, FlowNodeLabels
from .dtos import FlowLinkDTO, FlowNodeDTO


class NodeDescription(NamedTuple):
    kind: FlowNodeKind
    label: str
    category: AnalyticsCategory | None = None
    wallet: LedgerWallet | None = None


BALANCING_NODES = {
    FlowNodeIdentifiers.SAVINGS.value: NodeDescription(
        kind=FlowNodeKind.SAVINGS,
        label=FlowNodeLabels.SAVINGS.value,
    ),
    FlowNodeIdentifiers.RESERVES.value: NodeDescription(
        kind=FlowNodeKind.RESERVES,
        label=FlowNodeLabels.RESERVES.value,
    ),
}


class MoneyFlowGraph:
    def __init__(self, ledger: AnalyticsLedger, smallest_visible_amount: Decimal) -> None:
        self._ledger = ledger
        self._smallest_visible_amount = smallest_visible_amount
        self._node_descriptions: dict[str, NodeDescription] = dict(BALANCING_NODES)
        self._links: list[FlowLinkDTO] = []

    @property
    def links(self) -> list[FlowLinkDTO]:
        return sorted(self._links, key=lambda link: link.amount, reverse=True)

    @property
    def nodes(self) -> list[FlowNodeDTO]:
        incoming_amounts: dict[str, Decimal] = {}
        outgoing_amounts: dict[str, Decimal] = {}
        for link in self._links:
            incoming_amounts[link.target] = incoming_amounts.get(link.target, ZERO) + link.amount
            outgoing_amounts[link.source] = outgoing_amounts.get(link.source, ZERO) + link.amount

        linked_identifiers = dict.fromkeys(
            identifier for link in self._links for identifier in (link.source, link.target)
        )

        return [
            self._node_of(
                identifier,
                max(incoming_amounts.get(identifier, ZERO), outgoing_amounts.get(identifier, ZERO)),
            )
            for identifier in linked_identifiers
        ]

    def add_wallet(self, wallet: LedgerWallet, wallet_rows: list[LedgerRow]) -> None:
        wallet_node = f"{FlowNodeIdentifiers.WALLET_PREFIX}{wallet.identifier}"
        self._node_descriptions[wallet_node] = NodeDescription(
            kind=FlowNodeKind.WALLET,
            label=wallet.name,
            wallet=wallet,
        )

        category_amounts: dict[str, Decimal] = {}
        for row in wallet_rows:
            category_node = self._register_category_node(row)
            category_amounts[category_node] = category_amounts.get(
                category_node, ZERO
            ) + self._ledger.converted_magnitude(row)

        for category_node, amount in category_amounts.items():
            if self._node_descriptions[category_node].kind is FlowNodeKind.INCOME_CATEGORY:
                self._link(category_node, wallet_node, amount)
            else:
                self._link(wallet_node, category_node, amount)

        self._link_balance(
            wallet_node,
            wallet_inflow=self._ledger.converted_total(wallet_rows, LedgerSide.INCOME),
            wallet_outflow=self._ledger.converted_total(wallet_rows, LedgerSide.EXPENSE),
        )

    def _link_balance(
        self, wallet_node: str, wallet_inflow: Decimal, wallet_outflow: Decimal
    ) -> None:
        if wallet_inflow > wallet_outflow:
            self._link(
                wallet_node, FlowNodeIdentifiers.SAVINGS.value, wallet_inflow - wallet_outflow
            )
        elif wallet_outflow > wallet_inflow:
            self._link(
                FlowNodeIdentifiers.RESERVES.value, wallet_node, wallet_outflow - wallet_inflow
            )

    def _link(self, source: str, target: str, amount: Decimal) -> None:
        if amount >= self._smallest_visible_amount:
            self._links.append(FlowLinkDTO(source=source, target=target, amount=amount))

    def _register_category_node(self, row: LedgerRow) -> str:
        is_income = row.side is LedgerSide.INCOME
        prefix = (
            FlowNodeIdentifiers.INCOME_PREFIX if is_income else FlowNodeIdentifiers.EXPENSE_PREFIX
        )
        category_node = f"{prefix}{category_token(row.category)}"
        self._node_descriptions.setdefault(
            category_node,
            NodeDescription(
                kind=FlowNodeKind.INCOME_CATEGORY if is_income else FlowNodeKind.EXPENSE_CATEGORY,
                label=row.category.name
                if row.category is not None
                else FlowNodeLabels.UNCATEGORISED.value,
                category=row.category,
            ),
        )

        return category_node

    def _node_of(self, identifier: str, amount: Decimal) -> FlowNodeDTO:
        description = self._node_descriptions[identifier]

        return FlowNodeDTO(
            identifier=identifier,
            kind=description.kind,
            label=description.label,
            category=description.category,
            wallet=description.wallet,
            amount=amount,
        )
