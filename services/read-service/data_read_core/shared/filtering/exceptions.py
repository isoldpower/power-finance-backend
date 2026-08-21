from data_read_core.shared.http_contract import DetailCode, ErrorDetail, ValidationFailed

ROOT_PATH = "filter_body"


class FilterParseError(ValidationFailed, ValueError):
    detail_code: DetailCode = DetailCode.FILTER_MALFORMED_NODE

    def __init__(self, reason: str, *, path: str = ROOT_PATH) -> None:
        self.reason = reason
        self.path = path
        super().__init__(
            details=[
                ErrorDetail(field=path, code=self.detail_code, message=reason),
            ]
        )

    def __str__(self) -> str:
        return f"{self.path}: {self.reason}"


class InvalidOperationError(FilterParseError):
    """Operator is unknown, or not permitted on that field."""

    detail_code = DetailCode.FILTER_OPERATOR_NOT_ALLOWED


class InvalidValueError(InvalidOperationError):
    """`value` does not match the field's declared type."""

    detail_code = DetailCode.FILTER_VALUE_TYPE


class UnknownNodeError(InvalidOperationError):
    """Node is neither a valid group nor a valid leaf."""

    detail_code = DetailCode.FILTER_MALFORMED_NODE


class InvalidGroupingError(FilterParseError):
    """Group has zero or multiple keys."""

    detail_code = DetailCode.FILTER_MALFORMED_GROUP


class InvalidStructureError(FilterParseError):
    """Node is not an object at all."""

    detail_code = DetailCode.FILTER_MALFORMED_NODE


class InvalidGroupChildrenError(InvalidStructureError):
    """Group's child list is missing, not an array, or empty."""

    detail_code = DetailCode.FILTER_MALFORMED_GROUP


class PolicyViolationError(FilterParseError):
    """`field_name` is not whitelisted for this resource."""

    detail_code = DetailCode.FILTER_UNKNOWN_FIELD
