from rest_framework.request import Request

TARGET_PARAMETER = "target"
CODE_SEPARATOR = ","


def read_target_codes(request: Request) -> list[str] | None:
    """The requested codes, or `None` for "the whole map"."""

    raw_values = request.query_params.getlist(TARGET_PARAMETER)
    codes = [
        code.strip()
        for raw_value in raw_values
        for code in raw_value.split(CODE_SEPARATOR)
        if code.strip()
    ]

    return codes or None
