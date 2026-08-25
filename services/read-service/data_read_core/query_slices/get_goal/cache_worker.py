import json

from redis.asyncio import Redis

from .dtos import GoalDTO
from .infra import CACHE_TTL_SECONDS, get_single_cache_key


class CacheWorker:
    def __init__(self, redis_client: Redis) -> None:
        self._redis_client = redis_client

    async def try_serve_from_cache(
        self,
        goal_id: str,
        user_id: int,
    ) -> GoalDTO | None:
        cache_key = get_single_cache_key(goal_id)
        cached_value = await self._redis_client.get(cache_key)
        if cached_value is None:
            return None

        goal = GoalDTO.from_cache(json.loads(cached_value))
        if goal.user_id != user_id:
            await self._redis_client.delete(cache_key)
            return None

        return goal

    async def save_to_cache(
        self,
        goal: GoalDTO,
    ) -> None:
        cache_key = get_single_cache_key(goal.id)
        await self._redis_client.set(
            cache_key,
            json.dumps(goal.to_cache()),
            ex=CACHE_TTL_SECONDS,
        )
