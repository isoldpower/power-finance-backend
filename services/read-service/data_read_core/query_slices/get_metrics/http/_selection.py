from rest_framework.request import Request

from data_read_core.shared.http_contract import (
    DetailCode,
    ErrorDetail,
    ValidationFailed,
)

from ..config import ALL_SECTIONS, FALSE_STATEMENTS, TRUTH_STATEMENTS, Messages, Section


def read_sections(request: Request) -> frozenset[Section]:
    return frozenset(
        section
        for section in ALL_SECTIONS
        if _read_flag(
            request.query_params.get(section.value),
            section.value,
        )
    )


def _read_flag(raw_flag: str | None, parameter: str) -> bool:
    if raw_flag is None:
        return True

    query_statement = raw_flag.strip().lower()
    if query_statement in TRUTH_STATEMENTS:
        return True
    if query_statement in FALSE_STATEMENTS:
        return False

    raise ValidationFailed(
        details=[
            ErrorDetail(
                field=parameter,
                code=DetailCode.INVALID,
                message=Messages.NOT_A_BOOLEAN.format(
                    parameter=parameter,
                    legal=", ".join(sorted(TRUTH_STATEMENTS | FALSE_STATEMENTS)),
                ),
            )
        ]
    )
