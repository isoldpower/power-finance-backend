from dataclasses import dataclass
from enum import StrEnum


class ResolutionIntent(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    DANGER = "danger"


@dataclass(frozen=True)
class ActionResolution:
    resolution_id: str
    label: str
    intent: ResolutionIntent = ResolutionIntent.SECONDARY
    applies: bool = False
    dismissal: bool = False

    @classmethod
    def from_storage(cls, raw: dict) -> "ActionResolution":
        return cls(
            resolution_id=str(raw["resolution_id"]),
            label=str(raw["label"]),
            intent=ResolutionIntent(raw.get("intent", ResolutionIntent.SECONDARY)),
            applies=bool(raw.get("applies", False)),
            dismissal=bool(raw.get("dismissal", False)),
        )

    def to_storage(self) -> dict:
        return {
            "resolution_id": self.resolution_id,
            "label": self.label,
            "intent": str(self.intent),
            "applies": self.applies,
            "dismissal": self.dismissal,
        }
