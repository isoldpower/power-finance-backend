from dataclasses import dataclass


@dataclass(frozen=True)
class Currency:
    code: str
    name: str
    numeric: str
    digits: int
