from analytics.infrastructure.repositories.wallet_repository import WalletRepository
from analytics.infrastructure.selectors.money_flow_selector import MoneyFlowSelector

from ..dto import MoneyFlowResultDTO, MoneyFlowNodeDTO, MoneyFlowLinkDTO


class GetMoneyFlowQueryHandler:
    def __init__(
        self,
        wallet_repository: WalletRepository | None = None,
        money_flow_selector: MoneyFlowSelector | None = None
    ):
        self.wallet_repository = wallet_repository or WalletRepository()
        self.money_flow_selector = money_flow_selector or MoneyFlowSelector()

    def handle(self, user_id: str) -> MoneyFlowResultDTO:
        wallets = self.wallet_repository.get_ordered_user_wallets(user_id=user_id)

        if not wallets:
            return MoneyFlowResultDTO(nodes=[], links=[])

        nodes = [
            MoneyFlowNodeDTO(
                name=wallet.name,
                level=index,
            )
            for index, wallet in enumerate(wallets)
        ]

        wallet_index = {
            wallet.id: index
            for index, wallet in enumerate(wallets)
        }

        transfer_rows = self.money_flow_selector.get_user_transfers_grouped(user_id=user_id)

        links: list[MoneyFlowLinkDTO] = []
        seen_pairs: set[tuple[int, int]] = set()

        for row in transfer_rows:
            src = wallet_index.get(row["from_wallet_id"])
            dst = wallet_index.get(row["to_wallet_id"])

            if src is None or dst is None:
                continue

            if src == dst:
                continue

            if dst <= src:
                continue

            pair = (src, dst)
            if pair in seen_pairs:
                continue

            seen_pairs.add(pair)

            value = float(row["total"] or 0)
            if value <= 0:
                continue

            links.append(MoneyFlowLinkDTO(
                source_id=src,
                target_id=dst,
                value=value,
            ))

        return MoneyFlowResultDTO(nodes=nodes, links=links)

