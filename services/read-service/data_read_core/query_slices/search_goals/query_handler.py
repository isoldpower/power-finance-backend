from filter_grammar_py import GOAL_FILTER_POLICY

from data_read_core.shared.filtering import FilterTree
from data_read_core.shared.query_results import FetchedRows

from .dtos import GoalDTO, SearchGoalsQuery
from .infra import search_owned_goals
from .logger_shortcuts import log_search_served


class SearchGoalsQueryHandler:
    async def handle(self, query: SearchGoalsQuery) -> FetchedRows:
        filter_query = FilterTree(GOAL_FILTER_POLICY).resolve_es(query.filter_body)
        matched_documents, total = await search_owned_goals(
            user_id=query.user_id,
            filter_query=filter_query,
            page=query.page,
        )

        goals = [GoalDTO.from_es_hit(document) for document in matched_documents]
        log_search_served(query.user_id, len(goals), total)

        return FetchedRows(
            rows=goals,
            total=total,
            cached=False,
        )
