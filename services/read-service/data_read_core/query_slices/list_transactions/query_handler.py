from logging import getLogger

from .dtos import ListTransactionsQuery, TransactionDTO
from .infra import count_user_transactions, fetch_user_transactions

logger = getLogger("query_slices.list_transactions")


class ListTransactionsQueryHandler:
    async def handle(self, query: ListTransactionsQuery) -> tuple[list[TransactionDTO], int]:
        total = await count_user_transactions(query.user_id)
        database_entry = await fetch_user_transactions(query.user_id, query.limit, query.offset)
        transactions = [TransactionDTO.from_read_model(entry) for entry in database_entry]

        logger.info(
            "Served %d of %d transactions for user %s from read store.",
            len(transactions),
            total,
            query.user_id,
        )
        return transactions, total
