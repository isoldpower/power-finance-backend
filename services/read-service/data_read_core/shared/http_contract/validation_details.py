from collections.abc import Mapping
from dataclasses import dataclass
from functools import singledispatch
from typing import Any

from .codes import DetailCode
from .exceptions import ErrorDetail

PATH_SEPARATOR = "."
DRF_CODE_ATTRIBUTE = "code"

DETAIL_CODE_BY_DRF_CODE: dict[str, DetailCode] = {
    "required": DetailCode.REQUIRED,
    "null": DetailCode.REQUIRED,
    "blank": DetailCode.REQUIRED,
    "does_not_exist": DetailCode.NOT_A_REFERENCE,
    "incorrect_type": DetailCode.INVALID,
    "invalid": DetailCode.INVALID,
    "invalid_choice": DetailCode.INVALID,
    "max_value": DetailCode.OUT_OF_BOUNDS,
    "min_value": DetailCode.OUT_OF_BOUNDS,
    "max_length": DetailCode.OUT_OF_BOUNDS,
    "min_length": DetailCode.OUT_OF_BOUNDS,
}
DETAIL_CODE_BY_NAME: dict[str, DetailCode] = {code.value: code for code in DetailCode}


@dataclass(frozen=True)
class DetailPath:
    """A JSON path into the request body: `filter_body.and[1].or[0].field_name`."""

    segments: tuple[str, ...] = ()

    def child(self, key: str) -> "DetailPath":
        return DetailPath(self.segments + (key,))

    def element(self, position: int) -> "DetailPath":
        indexed = f"[{position}]"
        if not self.segments:
            return DetailPath((indexed,))

        return DetailPath(self.segments[:-1] + (self.segments[-1] + indexed,))

    @property
    def field(self) -> str | None:
        return PATH_SEPARATOR.join(self.segments) or None


ROOT_PATH = DetailPath()


def filter_detail_code_for(name: str) -> DetailCode:
    return DETAIL_CODE_BY_NAME.get(name, DetailCode.INVALID)


def detail_code_for(drf_code: Any) -> DetailCode:
    return DETAIL_CODE_BY_DRF_CODE.get(str(drf_code), DetailCode.INVALID)


@singledispatch
def flatten_validation_error(detail: Any, path: DetailPath = ROOT_PATH) -> list[ErrorDetail]:
    return [
        ErrorDetail(
            field=path.field,
            code=detail_code_for(getattr(detail, DRF_CODE_ATTRIBUTE, "")),
            message=str(detail),
        )
    ]


@flatten_validation_error.register(Mapping)
def _flatten_mapping(detail: Mapping, path: DetailPath = ROOT_PATH) -> list[ErrorDetail]:
    return [
        flattened
        for key, value in detail.items()
        for flattened in flatten_validation_error(value, path.child(str(key)))
    ]


@flatten_validation_error.register(list)
def _flatten_sequence(detail: list, path: DetailPath = ROOT_PATH) -> list[ErrorDetail]:
    return [
        flattened
        for position, value in enumerate(detail)
        for flattened in flatten_validation_error(value, _element_path(value, path, position))
    ]


@singledispatch
def _element_path(value: Any, path: DetailPath, position: int) -> DetailPath:
    return path


@_element_path.register(Mapping)
@_element_path.register(list)
def _container_element_path(value: Any, path: DetailPath, position: int) -> DetailPath:
    return path.element(position)
