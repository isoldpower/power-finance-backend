from .contracts import ActivitySource, Overview
from .infrastructure import OverviewCache
from .overview_builder import build_overview


class OverviewService:
    def __init__(self, activity: ActivitySource, cache: OverviewCache) -> None:
        self._activity = activity
        self._cache = cache

    async def read(self, external_id: str) -> tuple[Overview, bool]:
        cached = self._cache.get(external_id)
        if cached is not None:
            return cached, True

        overview = build_overview(await self._activity.read(external_id))
        self._cache.put(external_id, overview)

        return overview, False
