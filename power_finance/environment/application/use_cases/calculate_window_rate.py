from datetime import timedelta

from environment.application.interfaces import (
    WindowAlgorithm,
    CacheStorage,
)


class CalculateWindowRate:
    def __init__(
            self,
            window_algorithm: WindowAlgorithm | None = None,
            cache: CacheStorage | None = None,
    ) -> None:
        self._window_algorithm = window_algorithm
        self._cache_storage = cache
        self._redis = get_re

    def calculate(self, request_id: str, period: timedelta) -> int:

