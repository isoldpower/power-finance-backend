from data_read_core.shared.analytics import IntegerBounds, ParamsList

REPORT_NAME = "list_analytics_counterparties"

LIMIT_BOUNDS = IntegerBounds(parameter=ParamsList.LIMIT.value, default=10, minimum=1, maximum=25)
