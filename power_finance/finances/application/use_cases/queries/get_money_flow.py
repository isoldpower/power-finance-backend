from dataclasses import dataclass
from uuid import UUID

from finances.domain.entities import Wallet

from ...bootstrap import get_repository_registry
from ...dtos import (
    MoneyFlowResultDTO,
    MoneyFlowNodeDTO,
    MoneyFlowLinkDTO,
)
from ...interfaces import (
    WalletSelectorsCollection,
    TransactionSelectorsCollection,
)


@dataclass(frozen=True)
class GetMoneyFlowQuery:
    user_id: int


class GetMoneyFlowQueryHandler:
    wallet_selector: WalletSelectorsCollection
    transaction_selector: TransactionSelectorsCollection

    def __init__(
        self,
        wallet_selector: WalletSelectorsCollection | None = None,
        transaction_selector: TransactionSelectorsCollection | None = None,
    ) -> None:
        registry = get_repository_registry()
        self.wallet_selector = wallet_selector or registry.wallet_selectors
        self.transaction_selector = transaction_selector or registry.transaction_selectors

    def _build_links_list(
        self,
        wallets: list[Wallet],
        transfer_rows: list[dict[str, str]]
    ) -> list[MoneyFlowLinkDTO]:
        wallet_index = {
            wallet.id: index
            for index, wallet in enumerate(wallets)
        }
        links: list[MoneyFlowLinkDTO] = []
        seen_pairs: set[tuple[int, int]] = set()
        for row in transfer_rows:
            source_id = wallet_index.get(UUID(row["send_wallet__id"]))
            destination_id = wallet_index.get(UUID(row["receive_wallet__id"]))
            parties_pair = (source_id, destination_id)

            if (source_id is None or
                    destination_id is None or
                    source_id == destination_id or
                    destination_id <= source_id or
                    parties_pair in seen_pairs
            ):
                continue

            seen_pairs.add(parties_pair)
            transfer_value = float(row["total"] or 0)
            if transfer_value > 0:
                links.append(MoneyFlowLinkDTO(
                    source_id=source_id,
                    target_id=destination_id,
                    value=transfer_value,
                ))

        return links

    def handle(self, query: GetMoneyFlowQuery) -> MoneyFlowResultDTO:
        wallets = (self.wallet_selector.get_ordered_user_wallets(user_id=query.user_id)
            or [])
        transfer_rows = (self.transaction_selector.get_user_transfers_grouped(user_id=query.user_id)
            or [])

        nodes = [MoneyFlowNodeDTO(
            id=index,
            name=wallet.name,
            level=index,
        ) for index, wallet in enumerate(wallets)]
        links = (self._build_links_list(wallets, transfer_rows)
            if wallets and transfer_rows else [])

        return MoneyFlowResultDTO(
            nodes=nodes,
            links=links
        )
