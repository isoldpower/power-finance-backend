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

    def get_data(
            self,
            callback: Callable[[], TValue],
            key: str | None = None,
    ) -> TValue:
        final_key = f'{self.base_cache_key}{f":{key}" if key else ""}'
        requested_data = self.cache_instance.get(final_key)

        data: TValue
        if requested_data:
            data = requested_data
        else:
            data = callback()

        self.cache_instance.set(final_key, data)
        return data
