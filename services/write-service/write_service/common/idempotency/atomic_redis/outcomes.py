from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True, slots=True)
class StoredResponse:
    status_code: int
    body: Any
    headers: dict[str, str]
    request_hash: str


@dataclass(frozen=True, slots=True)
class Acquired:
    kind: Literal["acquired"] = "acquired"


@dataclass(frozen=True, slots=True)
class AlreadyCompleted:
    response: StoredResponse
    kind: Literal["completed"] = "completed"


@dataclass(frozen=True, slots=True)
class InProgress:
    kind: Literal["in_progress"] = "in_progress"


@dataclass(frozen=True, slots=True)
class Mismatch:
    stored_hash: str
    kind: Literal["mismatch"] = "mismatch"


AcquireResult = Acquired | AlreadyCompleted | InProgress | Mismatch


__all__ = [
    "Acquired",
    "AcquireResult",
    "AlreadyCompleted",
    "InProgress",
    "Mismatch",
    "StoredResponse",
]
