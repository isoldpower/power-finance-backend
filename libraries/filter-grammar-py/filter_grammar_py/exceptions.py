ROOT_PATH = "filter_body"
FILTER_UNKNOWN_FIELD = "filter_unknown_field"
FILTER_OPERATOR_NOT_ALLOWED = "filter_operator_not_allowed"
FILTER_VALUE_TYPE = "filter_value_type"
FILTER_MALFORMED_GROUP = "filter_malformed_group"
FILTER_MALFORMED_NODE = "filter_malformed_node"


class FilterParseError(ValueError):
    detail_code: str = FILTER_MALFORMED_NODE

    def __init__(self, reason: str, *, path: str = ROOT_PATH) -> None:
        self.reason = reason
        self.path = path
        super().__init__(f"{path}: {reason}")


class InvalidOperationError(FilterParseError):
    detail_code = FILTER_OPERATOR_NOT_ALLOWED


class InvalidValueError(InvalidOperationError):
    detail_code = FILTER_VALUE_TYPE


class UnknownNodeError(InvalidOperationError):
    detail_code = FILTER_MALFORMED_NODE


class InvalidGroupingError(FilterParseError):
    detail_code = FILTER_MALFORMED_GROUP


class InvalidStructureError(FilterParseError):
    detail_code = FILTER_MALFORMED_NODE


class InvalidGroupChildrenError(InvalidStructureError):
    detail_code = FILTER_MALFORMED_GROUP


class PolicyViolationError(FilterParseError):
    detail_code = FILTER_UNKNOWN_FIELD
