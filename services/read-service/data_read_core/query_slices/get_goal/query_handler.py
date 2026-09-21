import asyncio

from redis.asyncio import Redis

from data_read_core.shared.query_results import FetchedResource

from .cache_worker import CacheWorker
from .dtos import GetGoalQuery, GoalDetailDTO, GoalDTO, HistoryEntryDTO
from .exceptions import GoalNotFoundError
from .infra import (
    count_goal_history,
    fetch_goal_history,
    fetch_owned_goal,
    get_redis_client,
)
from .logger_shortcuts import log_served_from_cache, log_served_from_store


class GetGoalQueryHandler:
    def __init__(self, redis_client: Redis | None = None):
        redis_client = redis_client or get_redis_client()

        self._redis_client = redis_client
        self._cache_worker = CacheWorker(redis_client)

    async def handle(self, query: GetGoalQuery) -> FetchedResource:
        goal, cached = await self._load_goal(query)
        history_rows, history_total = await asyncio.gather(
            fetch_goal_history(goal.id, query.history_page),
            count_goal_history(goal.id),
        )

        return FetchedResource(
            resource=GoalDetailDTO(
                goal=goal,
                history=[HistoryEntryDTO.from_read_model(row) for row in history_rows],
                history_total=history_total,
            ),
            cached=cached,
        )

    async def _load_goal(self, query: GetGoalQuery) -> tuple[GoalDTO, bool]:
        cached_value = await self._cache_worker.try_serve_from_cache(
            query.goal_id,
            query.user_id,
        )
        if cached_value is not None:
            log_served_from_cache(query.goal_id)
            return cached_value, True

        owned_goal = await fetch_owned_goal(query.user_id, query.goal_id)
        if owned_goal is None:
            raise GoalNotFoundError()

        goal = GoalDTO.from_read_model(owned_goal)
        await self._cache_worker.save_to_cache(goal)

        log_served_from_store(query.goal_id)
        return goal, False
