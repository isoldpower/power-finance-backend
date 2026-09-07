from enum import IntEnum, StrEnum


class RefusalPath(StrEnum):
    TRIGGER = "trigger"
    EFFECTS = "effects"
    FILTER_BODY = "trigger.filter_body"


class RefusalCode(StrEnum):
    INVALID = "invalid"
    REQUIRED = "required"
    TRIGGER_FIELD_CONFLICT = "trigger_field_conflict"
    EFFECT_UNKNOWN_TYPE = "effect_unknown_type"
    EFFECT_PARAMS_INVALID = "effect_params_invalid"
    EFFECT_SUBJECT_MISMATCH = "effect_subject_mismatch"


class FieldSettings(IntEnum):
    CURRENCY_CODE_LENGTH = 3
