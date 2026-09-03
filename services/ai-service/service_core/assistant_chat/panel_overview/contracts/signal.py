from dataclasses import dataclass
from enum import StrEnum


class SignalTone(StrEnum):
    """How a signal should read, not what colour it is. A client maps these to
    its own palette."""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    MUTED = "muted"


@dataclass(frozen=True, slots=True)
class Signal:
    """A headline the panel shows above the conversation.

    `value` is a PREFORMATTED display string and is the one deliberate
    exception to the rule that this API never formats. It is a sentence
    fragment with no fixed unit and nothing for a client to compute from — it
    is text, rendered verbatim, and must never be parsed back into a number.
    """

    label: str
    value: str
    tone: SignalTone

    def as_dict(self) -> dict:
        return {"label": self.label, "value": self.value, "tone": str(self.tone)}
