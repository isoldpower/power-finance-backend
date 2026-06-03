from logging import getLogger

from .dtos import ListWalletsQuery, WalletDTO
from .infra import count_owned_wallets, fetch_owned_wallets

logger = getLogger("query_slices.list_wallets")


class ListWalletsQueryHandler:
    async def handle(self, query: ListWalletsQuery) -> tuple[list[WalletDTO], int]:
        total = await count_owned_wallets(query.user_id)
        database_entry = await fetch_owned_wallets(query.user_id, query.limit, query.offset)
        wallets = [WalletDTO.from_read_model(entry) for entry in database_entry]

        logger.info(
            "Served %d of %d wallets for user %s from read store.",
            len(wallets),
            total,
            query.user_id,
        )
        return wallets, total
