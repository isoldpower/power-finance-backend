import enum
import re
from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID


class TypeVariant(str, enum.Enum):
    INTEGER = 'int'
    FLOAT = 'float'
    STRING = 'str'
    BOOLEAN = 'bool'
    DATETIME = 'datetime'
    UUID = 'uuid'


class TypeValidator(ABC):
    value: str

    def __init__(self, value: str) -> None:
        self.value = value

    @abstractmethod
    def validate(self) -> bool:
        raise NotImplementedError()


class IntTypeValidator(TypeValidator):
    def validate(self) -> bool:
        pattern = r'^[+-]?\d+$'
        return bool(re.fullmatch(pattern, self.value))


class FloatTypeValidator(TypeValidator):
    def validate(self) -> bool:
        pattern = r'^[+-]?(\d+\.\d+|\d+|\.\d+)$'
        return bool(re.fullmatch(pattern, self.value))


class StringTypeValidator(TypeValidator):
    def validate(self) -> bool:
        return True


class BooleanTypeValidator(TypeValidator):
    def validate(self) -> bool:
        if isinstance(self.value, bool):
            return True
        pattern = r'^(true|false|1|0)$'
        return bool(re.fullmatch(pattern, str(self.value), re.IGNORECASE))


class DatetimeTypeValidator(TypeValidator):
    def validate(self) -> bool:
        try:
            normalized = self.value.replace("Z", "+00:00")
            datetime.fromisoformat(normalized)
            return True
        except ValueError:
            return False


class UUIDTypeValidator(TypeValidator):
    def validate(self) -> bool:
        try:
            UUID(self.value)
            return True
        except ValueError:
            return False


class TypeValidatorBuilder:
    _known_validators: dict[TypeVariant, type[TypeValidator]] = {
        TypeVariant.INTEGER: IntTypeValidator,
        TypeVariant.FLOAT: FloatTypeValidator,
        TypeVariant.STRING: StringTypeValidator,
        TypeVariant.BOOLEAN: BooleanTypeValidator,
        TypeVariant.DATETIME: DatetimeTypeValidator,
        TypeVariant.UUID: UUIDTypeValidator,
    }

    @staticmethod
    def build_validator(variant: TypeVariant, value: str) -> TypeValidator:
        validator_type = TypeValidatorBuilder._known_validators.get(variant)
        if validator_type is None:
            raise TypeError(f"Unknown type for variant {variant}. Received value {value}")

        return validator_type(value)
