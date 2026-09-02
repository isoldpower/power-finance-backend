from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RunContext:
    user_id: int
    user_external_id: str
    automation_id: str
    automation_name: str
    subject_type: str
    subject_id: UUID

    @property
    def subject(self) -> tuple[str, str]:
        return self.subject_type, str(self.subject_id)
