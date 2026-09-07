from dataclasses import dataclass


@dataclass(frozen=True)
class AutomationRefusal(ValueError):
    path: str
    detail_code: str
    reason: str

    def __str__(self) -> str:
        return f"{self.path}: {self.reason}"
