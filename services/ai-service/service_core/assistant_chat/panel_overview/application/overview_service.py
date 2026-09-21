from ..domain.entities import Overview
from ..domain.overview_builder import build_overview
from .contracts import ActivitySource, OverviewCache
from .dtos import dto_to_activity, dto_to_overview, overview_to_dto


class OverviewService:
    def __init__(self, activity: ActivitySource, cache: OverviewCache) -> None:
        self._activity = activity
        self._cache = cache

    async def read(self, external_id: str) -> tuple[Overview, bool]:
        cached = self._cache.get(external_id)
        if cached is not None:
            return dto_to_overview(cached), True

        overview = build_overview(dto_to_activity(await self._activity.read(external_id)))
        self._cache.put(external_id, overview_to_dto(overview))

        return overview, False
