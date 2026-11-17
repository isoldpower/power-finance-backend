from dataclasses import dataclass

from .scope import AnalyticsScope


@dataclass(frozen=True)
class ScopedAnalyticsQuery:
    scope: AnalyticsScope

    @property
    def user_id(self) -> int:
        return self.scope.user_id

    @property
    def report_parameters(self) -> dict:
        return {}

    @property
    def cache_signature(self) -> dict:
        return {**self.scope.cache_signature, **self.report_parameters}
