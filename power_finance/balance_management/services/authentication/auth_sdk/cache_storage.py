from typing import Callable

from django.core.cache import cache


class CacheStorage:
    def __init__(self, cache_key):
        self.cache_key = cache_key
        self.cache_instance = cache

    def get_data(self, callback: Callable[[], dict]) -> dict:
        requested_data = self.cache_instance.get(self.cache_key)

        data: dict
        if requested_data:
            data = requested_data
        else:
            data = callback()

        self.cache_instance.set(self.cache_key, data)
        return data

