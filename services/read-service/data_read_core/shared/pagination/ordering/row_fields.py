from collections.abc import Mapping
from functools import singledispatch
from typing import Any


@singledispatch
def read_row_field(row: Any, field_name: str) -> Any:
    return getattr(row, field_name)


@read_row_field.register(Mapping)
def _read_mapping_field(row: Mapping, field_name: str) -> Any:
    return row.get(field_name)
