from dataclasses import dataclass
from enum import StrEnum


class SignalTone(StrEnum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    MUTED = "muted"


@dataclass(frozen=True, slots=True)
class Signal:
    label: str
    value: str
    tone: SignalTone

    def as_dict(self) -> dict:
        return {"label": self.label, "value": self.value, "tone": str(self.tone)}
