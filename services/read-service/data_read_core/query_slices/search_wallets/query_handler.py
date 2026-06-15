from data_read_core.shared.filtering import FilterTree

from .dtos import SearchWalletsQuery, WalletDTO
from .infra import search_owned_wallets
from .logger_shortcuts import log_search_served
from .policy import WALLET_FILTER_POLICY


class SearchWalletsQueryHandler:
    """Search is served straight from Elasticsearch with no Redis caching. The
    view gates on the ES applied-seq (es_read_at_least_gate), so a Read-At-Least
    header is honoured against the ES projection's own progress."""

    async def handle(self, query: SearchWalletsQuery) -> tuple[list[WalletDTO], int]:
        filter_query = FilterTree(WALLET_FILTER_POLICY).resolve_es(query.filter_body)
        sources, total = await search_owned_wallets(
            user_id=query.user_id,
            filter_query=filter_query,
            limit=query.limit,
            offset=query.offset,
        )

        wallets = [WalletDTO.from_es_hit(source) for source in sources]
        log_search_served(query.user_id, len(wallets), total)

        return wallets, total
