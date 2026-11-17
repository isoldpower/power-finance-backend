from data_read_core.shared.analytics import IntegerBounds, ParamsList

REPORT_NAME = "get_analytics_balance_history"

POINTS_BOUNDS = IntegerBounds(parameter=ParamsList.POINTS.value, default=40, minimum=2, maximum=120)
