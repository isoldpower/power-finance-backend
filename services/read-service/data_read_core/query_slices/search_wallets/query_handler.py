from data_read_core.shared.filtering import WALLET_FILTER_POLICY, FilterTree
from data_read_core.shared.query_results import FetchedRows

from .dtos import SearchWalletsQuery, WalletDTO
from .infra import search_owned_wallets
from .logger_shortcuts import log_search_served


class SearchWalletsQueryHandler:
    """Search is served straight from Elasticsearch with no Redis caching."""

    async def handle(self, query: SearchWalletsQuery) -> FetchedRows:
        filter_query = FilterTree(WALLET_FILTER_POLICY).resolve_es(query.filter_body)
        sources, total = await search_owned_wallets(
            user_id=query.user_id,
            filter_query=filter_query,
            page=query.page,
        )

        wallets = [WalletDTO.from_es_hit(source) for source in sources]
        log_search_served(query.user_id, len(wallets), total)

        return FetchedRows(rows=wallets, total=total, cached=False)
