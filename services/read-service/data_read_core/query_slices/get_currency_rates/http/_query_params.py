from rest_framework.request import Request

from ..config import CODE_SEPARATOR, ParamsList


def read_target_codes(request: Request) -> list[str] | None:
    raw_values = request.query_params.getlist(ParamsList.TARGET)
    codes = [
        code.strip()
        for raw_value in raw_values
        for code in raw_value.split(CODE_SEPARATOR)
        if code.strip()
    ]

    return codes or None
