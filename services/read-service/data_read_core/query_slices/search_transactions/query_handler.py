from data_read_core.shared.filtering import FilterTree

from .dtos import SearchTransactionsQuery, TransactionDTO
from .infra import search_owned_transactions
from .logger_shortcuts import log_search_served
from .policy import TRANSACTION_FILTER_POLICY


class SearchTransactionsQueryHandler:
    """Search is served straight from Elasticsearch with no Redis caching. The
    view gates on the ES applied-seq (es_read_at_least_gate), so a Read-At-Least
    header is honoured against the ES projection's own progress."""

    async def handle(self, query: SearchTransactionsQuery) -> tuple[list[TransactionDTO], int]:
        filter_query = FilterTree(TRANSACTION_FILTER_POLICY).resolve_es(query.filter_body)
        sources, total = await search_owned_transactions(
            user_id=query.user_id,
            filter_query=filter_query,
            limit=query.limit,
            offset=query.offset,
        )

        transactions = [TransactionDTO.from_es_hit(source) for source in sources]
        log_search_served(query.user_id, len(transactions), total)

        return transactions, total
