from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AccountSpec:
    group: str
    name: str
