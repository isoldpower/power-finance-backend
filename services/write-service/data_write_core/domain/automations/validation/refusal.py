from dataclasses import dataclass

TRIGGER_PATH = "trigger"
EFFECTS_PATH = "effects"
FILTER_BODY_PATH = "trigger.filter_body"

INVALID = "invalid"
REQUIRED = "required"
TRIGGER_FIELD_CONFLICT = "trigger_field_conflict"
EFFECT_UNKNOWN_TYPE = "effect_unknown_type"
EFFECT_PARAMS_INVALID = "effect_params_invalid"
EFFECT_SUBJECT_MISMATCH = "effect_subject_mismatch"


@dataclass(frozen=True)
class AutomationRefusal(ValueError):
    path: str
    detail_code: str
    reason: str

    def __str__(self) -> str:
        return f"{self.path}: {self.reason}"
