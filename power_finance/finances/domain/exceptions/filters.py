class FilterParseError(ValueError):
    pass


class InvalidOperationError(FilterParseError):
    pass

class InvalidGroupingError(FilterParseError):
    pass

class InvalidStructureError(FilterParseError):
    pass

class PolicyViolationError(FilterParseError):
    pass