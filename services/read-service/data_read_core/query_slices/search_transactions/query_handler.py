from data_read_core.shared.filtering import TRANSACTION_FILTER_POLICY, FilterTree
from data_read_core.shared.query_results import FetchedRows

from .dtos import SearchTransactionsQuery, TransactionDTO
from .infra import search_owned_transactions
from .logger_shortcuts import log_search_served


class SearchTransactionsQueryHandler:
    """Search is served straight from Elasticsearch with no Redis caching."""

    async def handle(self, query: SearchTransactionsQuery) -> FetchedRows:
        filter_query = FilterTree(TRANSACTION_FILTER_POLICY).resolve_es(query.filter_body)
        sources, total = await search_owned_transactions(
            user_id=query.user_id,
            filter_query=filter_query,
            page=query.page,
        )

        transactions = [TransactionDTO.from_es_hit(source) for source in sources]
        log_search_served(query.user_id, len(transactions), total)

        return FetchedRows(rows=transactions, total=total, cached=False)
