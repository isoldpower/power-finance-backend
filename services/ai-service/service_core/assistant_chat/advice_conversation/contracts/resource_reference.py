from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResourceReference:
    type: str
    id: UUID

    def as_dict(self) -> dict:
        return {
            "type": self.type,
            "id": str(self.id),
        }
