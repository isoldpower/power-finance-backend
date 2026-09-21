from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum

from rest_framework import serializers
from rest_framework.request import Request

from data_read_core.shared.http_contract import (
    DetailCode,
    ErrorDetail,
    ValidationFailed,
)
from data_read_core.shared.pagination import (
    LimitPolicy,
)


class PointsCount(IntEnum):
    DEFAULT_POINTS = 10
    MINIMUM_POINTS = 1
    MAXIMUM_POINTS = 100


SINCE_FIELD = serializers.DateTimeField()
POINTS_LIMIT_POLICY = LimitPolicy(
    default=PointsCount.DEFAULT_POINTS,
    minimum=PointsCount.MINIMUM_POINTS,
    maximum=PointsCount.MAXIMUM_POINTS,
    parameter="points",
)


@dataclass(frozen=True)
class MetricsWindow:
    since: datetime | None

    @property
    def is_all_time(self) -> bool:
        return self.since is None

    @property
    def cache_signature(self) -> str:
        return self.since.isoformat() if self.since else "all"


def read_since(request: Request) -> MetricsWindow:
    raw_since = request.query_params.get("since")
    if not raw_since:
        return MetricsWindow(since=None)

    try:
        return MetricsWindow(since=SINCE_FIELD.to_internal_value(raw_since))
    except serializers.ValidationError as exc:
        raise ValidationFailed(
            details=[
                ErrorDetail(
                    field="since",
                    code=DetailCode.INVALID,
                    message="since must be an ISO-8601 datetime",
                )
            ]
        ) from exc


def read_points(request: Request) -> int:
    return POINTS_LIMIT_POLICY.resolve(request.query_params.get("points"))
