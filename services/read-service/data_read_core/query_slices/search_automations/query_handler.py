from filter_grammar_py import AUTOMATION_FILTER_POLICY

from data_read_core.shared.filtering import FilterTree
from data_read_core.shared.query_results import FetchedRows

from .dtos import AutomationDTO, SearchAutomationsQuery
from .infra import search_owned_automations
from .logger_shortcuts import log_search_served


class SearchAutomationsQueryHandler:
    async def handle(self, query: SearchAutomationsQuery) -> FetchedRows:
        filter_query = FilterTree(AUTOMATION_FILTER_POLICY).resolve_es(query.filter_body)
        matched_documents, total = await search_owned_automations(
            user_id=query.user_id,
            filter_query=filter_query,
            page=query.page,
        )

        automations = [AutomationDTO.from_es_hit(document) for document in matched_documents]
        log_search_served(query.user_id, len(automations), total)

        return FetchedRows(
            rows=automations,
            total=total,
            cached=False,
        )
