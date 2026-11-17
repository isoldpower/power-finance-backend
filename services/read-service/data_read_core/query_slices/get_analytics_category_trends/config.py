from enum import StrEnum

from data_read_core.shared.analytics import IntegerBounds, ParamsList

REPORT_NAME = "get_analytics_category_trends"

LIMIT_BOUNDS = IntegerBounds(parameter=ParamsList.LIMIT.value, default=6, minimum=1, maximum=7)


class SeriesKind(StrEnum):
    CATEGORY = "category"
    OTHER = "other"
