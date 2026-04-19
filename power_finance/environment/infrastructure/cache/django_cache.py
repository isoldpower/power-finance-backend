import asyncio
from typing import Callable, TypeVar

from django.core.cache import cache, BaseCache

from environment.application.interfaces import CacheStorage


TValue = TypeVar("TValue", bound=object)


class DjangoCacheStorage(CacheStorage):
    cache_instance: BaseCache
    base_cache_key: str

    def __init__(self, cache_key: str):
        self.cache_instance = cache
        self.base_cache_key = cache_key

    async def get_data(
            self,
            callback: Callable[[], TValue],
            key: str | None = None,
    ) -> TValue:
        final_key = f'{self.base_cache_key}{f":{key}" if key else ""}'
        requested_data = await self.cache_instance.aget(final_key)

        if requested_data:
            data = requested_data
        else:
            result = callback()
            data = await result if asyncio.iscoroutine(result) else result

        await self.cache_instance.aset(final_key, data)
        return data
