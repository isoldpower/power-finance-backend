from ..vocabulary import TypeVariant
from .base import ValueType
from .boolean_type import BooleanType
from .datetime_type import DateTimeType
from .decimal_type import DecimalType
from .float_type import FloatType
from .integer_type import IntegerType
from .string_type import StringType
from .uuid_type import UuidType

VALUE_TYPES: dict[TypeVariant, ValueType] = {
    value_type.variant: value_type
    for value_type in (
        IntegerType(),
        FloatType(),
        DecimalType(),
        StringType(),
        BooleanType(),
        DateTimeType(),
        UuidType(),
    )
}


def value_type_for(variant: TypeVariant) -> ValueType:
    return VALUE_TYPES[variant]
