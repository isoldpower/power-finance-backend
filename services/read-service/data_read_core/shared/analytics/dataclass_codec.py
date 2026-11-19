import dataclasses
import types
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Union, get_args, get_origin, get_type_hints


def encode_for_cache(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            dataclass_field.name: encode_for_cache(getattr(value, dataclass_field.name))
            for dataclass_field in dataclasses.fields(value)
        }
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, list | tuple):
        return [encode_for_cache(element) for element in value]
    if isinstance(value, dict):
        return {str(key): encode_for_cache(element) for key, element in value.items()}

    return value


def decode_from_cache(annotation: Any, raw_value: Any) -> Any:
    if raw_value is None:
        return None

    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        concrete_annotation = next(
            argument for argument in get_args(annotation) if argument is not type(None)
        )
        return decode_from_cache(concrete_annotation, raw_value)
    if origin is list:
        (element_annotation,) = get_args(annotation)
        return [decode_from_cache(element_annotation, element) for element in raw_value]
    if origin is tuple:
        element_annotation = get_args(annotation)[0]
        return tuple(decode_from_cache(element_annotation, element) for element in raw_value)
    if origin is dict:
        key_annotation, value_annotation = get_args(annotation)
        return {
            decode_from_cache(key_annotation, key): decode_from_cache(value_annotation, element)
            for key, element in raw_value.items()
        }
    if dataclasses.is_dataclass(annotation):
        dataclass_type: Any = annotation
        field_annotations = get_type_hints(dataclass_type)
        return dataclass_type(
            **{
                dataclass_field.name: decode_from_cache(
                    field_annotations[dataclass_field.name],
                    raw_value[dataclass_field.name],
                )
                for dataclass_field in dataclasses.fields(dataclass_type)
            }
        )
    if isinstance(annotation, type) and issubclass(annotation, Enum):
        return annotation(raw_value)
    if annotation is Decimal:
        return Decimal(raw_value)
    if annotation is datetime:
        return datetime.fromisoformat(raw_value)
    if annotation is date:
        return date.fromisoformat(raw_value)

    return raw_value
