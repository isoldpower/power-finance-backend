from datetime import datetime
from enum import StrEnum
from uuid import UUID

from rest_framework import serializers
from rest_framework.request import Request

from data_read_core.shared.http_contract import DetailCode, ErrorDetail, ValidationFailed

from .config import LIST_SEPARATOR, IntegerBounds, Messages, ParamsList

DATETIME_FIELD = serializers.DateTimeField()


def read_bounded_integer(
    request: Request,
    bounds: IntegerBounds,
    detail_code: DetailCode,
) -> int:
    raw_value = (request.query_params.get(bounds.parameter) or "").strip()
    if not raw_value:
        return bounds.default

    try:
        parsed_value = int(raw_value)
    except ValueError:
        parsed_value = None

    if parsed_value is None or not bounds.minimum <= parsed_value <= bounds.maximum:
        raise invalid_parameter(
            bounds.parameter,
            detail_code,
            Messages.INTEGER_OUT_OF_RANGE.format(
                parameter=bounds.parameter,
                minimum=bounds.minimum,
                maximum=bounds.maximum,
            ),
        )

    return parsed_value


def read_choice[ChoiceType: StrEnum](
    request: Request,
    parameter: ParamsList,
    choices: type[ChoiceType],
    detail_code: DetailCode,
    message: Messages,
) -> ChoiceType | None:
    raw_choice = (request.query_params.get(parameter) or "").strip().lower()
    if not raw_choice:
        return None

    try:
        return choices(raw_choice)
    except ValueError:
        raise invalid_parameter(
            parameter,
            detail_code,
            message.format(legal=", ".join(choice.value for choice in choices)),
        ) from None


def read_datetime(request: Request, parameter: ParamsList) -> datetime | None:
    raw_datetime = (request.query_params.get(parameter) or "").strip()
    if not raw_datetime:
        return None

    try:
        return DATETIME_FIELD.to_internal_value(raw_datetime)
    except serializers.ValidationError:
        raise invalid_parameter(
            parameter,
            DetailCode.RANGE_INVALID,
            Messages.UNPARSABLE_DATETIME.format(parameter=parameter),
        ) from None


def read_list(request: Request, parameter: ParamsList) -> list[str] | None:
    listed_values = [
        listed_value.strip()
        for raw_value in request.query_params.getlist(parameter)
        for listed_value in raw_value.split(LIST_SEPARATOR)
        if listed_value.strip()
    ]

    return listed_values or None


def normalised_uuid(raw_identifier: str) -> str | None:
    try:
        return str(UUID(raw_identifier))
    except ValueError:
        return None


def invalid_parameter(parameter: str, detail_code: DetailCode, message: str) -> ValidationFailed:
    return ValidationFailed(
        details=[
            ErrorDetail(
                field=str(parameter),
                code=detail_code,
                message=message,
            )
        ]
    )
